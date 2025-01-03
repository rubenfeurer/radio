#!/bin/bash

APP_NAME="radio"
VENV_PATH="/home/radio/radio/venv"
APP_PATH="/home/radio/radio/src/api/main.py"
LOG_FILE="/home/radio/radio/logs/radio.log"
PID_FILE="/tmp/${APP_NAME}.pid"
NODE_ENV="production"

# Check if running in Docker
if [ -f /.dockerenv ]; then
    echo "Running in Docker environment - skipping system checks"
    # Simplified startup for Docker
    exec "$VENV_PATH/bin/python" -m uvicorn src.api.main:app --host "0.0.0.0" --port "$API_PORT" --reload
    exit 0
fi

# Get configuration from Python
get_config() {
    source $VENV_PATH/bin/activate
    API_PORT=$(python3 -c "from config.config import settings; print(settings.API_PORT)")
    DEV_PORT=$(python3 -c "from config.config import settings; print(settings.DEV_PORT)")
    HOSTNAME=$(python3 -c "from config.config import settings; print(settings.HOSTNAME)")
}

check_ports() {
    get_config
    echo "Checking for processes using ports..."

    if [ -n "$DEV_PORT" ]; then
        for pid in $(lsof -ti :$DEV_PORT 2>/dev/null); do
            echo "Killing process $pid using port $DEV_PORT..."
            sudo kill -9 $pid 2>/dev/null || true
        done
    fi

    if [ -n "$API_PORT" ]; then
        for pid in $(sudo lsof -ti :$API_PORT 2>/dev/null); do
            echo "Killing process $pid using port $API_PORT..."
            sudo kill -9 $pid 2>/dev/null || true
        done
    fi

    # Additional cleanup
    sudo pkill -f "uvicorn.*$APP_PATH" || true
    pkill -f "npm run dev" || true
    pkill -f "vite" || true

    sleep 3

    if [ -n "$DEV_PORT" ] && [ -n "$API_PORT" ]; then
        if lsof -ti :$DEV_PORT 2>/dev/null || sudo lsof -ti :$API_PORT 2>/dev/null; then
            echo "Error: Ports still in use after cleanup"
            exit 1
        fi
    fi
}

validate_installation() {
    echo "Validating radio installation..."

    # Run checks in parallel
    (
        # Check radio user and groups
        if ! id radio >/dev/null 2>&1; then
            echo "Error: radio user does not exist"
            exit 1
        fi
    ) &

    (
        # Check services in parallel
        while read -r line; do
            [[ $line =~ ^#.*$ ]] && continue
            [[ -z $line ]] && continue

            case "$line" in
                "pigpio") systemctl is-active --quiet pigpiod ||
                    { echo "Error: pigpiod not running"; exit 1; } ;;
                "network-manager") systemctl is-active --quiet NetworkManager ||
                    { echo "Error: NetworkManager not running"; exit 1; } ;;
                "avahi-daemon"|"dnsmasq"|"hostapd") systemctl is-active --quiet "$line" ||
                    { echo "Error: $line not running"; exit 1; } ;;
            esac
        done < /home/radio/radio/install/system-requirements.txt
    ) &

    # Wait for all checks to complete
    wait
}

ensure_client_mode() {
    echo "Ensuring client mode on startup..."
    source $VENV_PATH/bin/activate

    # Create directory and initial mode file if it doesn't exist
    sudo mkdir -p /tmp/radio
    if [ ! -f "/tmp/radio/radio_mode.json" ]; then
        echo '{"mode": "CLIENT"}' | sudo tee /tmp/radio/radio_mode.json > /dev/null
    fi
    sudo chown -R radio:radio /tmp/radio

    python3 -c "
from src.core.mode_manager import ModeManagerSingleton
import asyncio
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('mode_switch')

async def ensure_client():
    try:
        manager = ModeManagerSingleton.get_instance()
        await manager.enable_client_mode()
        logger.info('Client mode switch completed')
    except Exception as e:
        logger.error(f'Error in mode switch: {str(e)}', exc_info=True)

asyncio.run(ensure_client())
"
}

validate_network() {
    echo "Validating network services..."

    # Check for conflicting services
    NETWORK_SERVICES=(
        "dhcpcd"
        "wpa_supplicant"
        "systemd-networkd"
        "raspberrypi-net-mods"
    )

    # Ensure conflicting services remain disabled
    for service in "${NETWORK_SERVICES[@]}"; do
        if systemctl is-active --quiet $service; then
            echo "Warning: Disabling conflicting service: $service"
            systemctl stop $service
            systemctl mask $service
        fi
    done

    # Verify NetworkManager is running
    if ! systemctl is-active --quiet NetworkManager; then
        echo "Restarting NetworkManager..."
        systemctl restart NetworkManager
        sleep 2
    fi

    # Verify wlan0 interface exists
    if ! ip link show wlan0 >/dev/null 2>&1; then
        echo "Warning: wlan0 interface not found"
        # Trigger udev rules reload
        udevadm control --reload-rules
        udevadm trigger --action=add
    fi
}

start() {
    echo "Starting $APP_NAME..."
    get_config

    # Run validations in parallel
    validate_installation &
    validate_network &
    ensure_client_mode &
    wait

    # Start services
    check_ports

    # Start FastAPI server and web server in parallel
    (
        echo "Starting FastAPI server on port $API_PORT..."
        nohup sudo -E env "PATH=$PATH" \
            "PYTHONPATH=/home/radio/radio" \
            "XDG_RUNTIME_DIR=/run/user/1000" \
            "PULSE_RUNTIME_PATH=/run/user/1000/pulse" \
            "$VENV_PATH/bin/python" -m uvicorn src.api.main:app \
            --host "0.0.0.0" \
            --port "$API_PORT" \
            --log-level debug \
            > $LOG_FILE 2>&1 &
        echo $! > $PID_FILE
    ) &

    if [ "$DEV_MODE" = true ]; then
        (
            echo "Starting web server in development mode..."
            cd /home/radio/radio/web
            sudo -u radio NODE_ENV=development \
                HOME=/home/radio \
                npm run dev -- \
                --host "0.0.0.0" \
                --port "$DEV_PORT" \
                >> "$WEB_LOG_FILE" 2>&1 &
            echo $! >> $PID_FILE
        ) &
    fi

    wait
}

stop() {
    if [ -f $PID_FILE ]; then
        while read PID; do
            echo "Stopping process with PID $PID..."
            sudo kill -15 $PID 2>/dev/null || true
            sleep 2
            sudo kill -9 $PID 2>/dev/null || true
        done < $PID_FILE
        rm -f $PID_FILE
        echo "$APP_NAME stopped."

        sudo pkill -f "uvicorn.*$APP_PATH"
        pkill -f "npm run dev"
    else
        echo "$APP_NAME is not running."
    fi

    check_ports
}

restart() {
    echo "Restarting $APP_NAME..."
    stop
    sleep 2
    start
}

status() {
    get_config
    if [ -f $PID_FILE ]; then
        PID=$(cat $PID_FILE)
        if ps -p $PID > /dev/null; then
            echo "$APP_NAME is running with PID $PID"
            echo "API Port: $API_PORT"
            echo "Dev Port: $DEV_PORT"
            echo "Recent logs:"
            tail -n 5 $LOG_FILE
        else
            echo "$APP_NAME is not running (stale PID file found)"
            rm -f $PID_FILE
        fi
    else
        echo "$APP_NAME is not running"
    fi
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
esac
