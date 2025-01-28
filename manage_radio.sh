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
    exec "$VENV_PATH/bin/python" -m uvicorn src.api.main:app --host "0.0.0.0" --port "$CONTAINER_PORT" --reload
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

    # Check and start required services with NOPASSWD sudo
    for service in avahi-daemon dnsmasq NetworkManager pigpiod; do
        echo "Starting $service..."
        sudo systemctl start $service || echo "Warning: Could not start $service"
    done

    # Verify MPV installation
    if ! ldconfig -p | grep libmpv > /dev/null; then
        echo "Error: libmpv not found in system library path"
        exit 1
    fi
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

    # Reset WiFi interface only if it's down
    if ! ip link show wlan0 | grep -q "UP"; then
        echo "Resetting WiFi interface..."
        sudo ip link set wlan0 down
        sudo rfkill unblock wifi
        sudo ip link set wlan0 up
        sleep 2
    fi

    # Only restart NetworkManager if it's not working
    if ! systemctl is-active --quiet NetworkManager; then
        echo "Restarting NetworkManager..."
        sudo systemctl restart NetworkManager
        sleep 3
    fi

    # Ensure wpa_supplicant is running
    if ! systemctl is-active --quiet wpa_supplicant; then
        echo "Starting wpa_supplicant..."
        sudo systemctl unmask wpa_supplicant
        sudo systemctl enable wpa_supplicant
        sudo systemctl start wpa_supplicant
        sleep 2
    fi

    # Only stop truly conflicting services
    for service in "systemd-networkd"; do
        if systemctl is-active --quiet $service; then
            echo "Stopping conflicting service: $service"
            sudo systemctl stop $service
            sudo systemctl mask $service
        fi
    done

    # Ensure interface is managed by NetworkManager
    echo "Setting wlan0 as managed..."
    sudo nmcli device set wlan0 managed yes

    # Wait for interface to become available
    echo "Waiting for WiFi interface..."
    for i in {1..10}; do
        if nmcli device status | grep "wlan0" | grep -q "disconnected"; then
            echo "WiFi interface is ready"
            break
        fi
        sleep 1
    done
}

setup_network_services() {
    echo "Setting up network services..."

    # Stop all network services first
    for service in dnsmasq avahi-daemon NetworkManager wpa_supplicant; do
        sudo systemctl stop $service
    done

    # Unmask and enable services in correct order
    echo "Starting wpa_supplicant..."
    sudo systemctl unmask wpa_supplicant
    sudo systemctl enable wpa_supplicant
    sudo systemctl start wpa_supplicant
    sleep 2

    echo "Starting NetworkManager..."
    sudo systemctl enable NetworkManager
    sudo systemctl start NetworkManager
    sleep 2

    echo "Starting dnsmasq..."
    sudo systemctl enable dnsmasq
    sudo systemctl start dnsmasq

    echo "Starting avahi-daemon..."
    sudo systemctl enable avahi-daemon
    sudo systemctl start avahi-daemon

    # Verify network interface
    echo "Setting up WiFi interface..."
    sudo ip link set wlan0 up
    sudo rfkill unblock wifi

    # Wait for NetworkManager to manage the interface
    sleep 3
    sudo nmcli device set wlan0 managed yes
}

setup_system() {
    echo "Setting up system dependencies..."

    # Create required directories
    sudo mkdir -p /home/radio/radio/logs
    sudo chown -R radio:radio /home/radio/radio/logs

    # Install system packages
    sudo apt-get update
    sudo apt-get install -y \
        libmpv1 \
        libmpv-dev \
        mpv \
        dnsmasq \
        network-manager \
        wireless-tools \
        wpasupplicant \
        firmware-brcm80211

    # Create symlink for libmpv in standard locations
    sudo ln -sf /usr/lib/*/libmpv.so.1 /usr/lib/libmpv.so
    sudo ln -sf /usr/lib/*/libmpv.so.1 /usr/local/lib/libmpv.so
    sudo ldconfig

    # Verify MPV installation
    if ! ldconfig -p | grep libmpv > /dev/null; then
        echo "Error: libmpv not found after installation"
        exit 1
    fi

    # Set up network services
    setup_network_services

    # Now install Python packages
    source $VENV_PATH/bin/activate
    pip install -r /home/radio/radio/install/requirements.txt
    deactivate

    # Add radio user to required groups
    sudo usermod -aG audio,video,netdev radio

    echo "Setup completed successfully"
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
    setup)
        setup_system
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|setup}"
        exit 1
        ;;
esac
