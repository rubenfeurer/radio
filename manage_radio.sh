#!/bin/bash

APP_NAME="radio"
VENV_PATH="/home/radio/radio/venv"
APP_PATH="/home/radio/radio/src/api/main.py"
LOG_FILE="/home/radio/radio/logs/radio.log"
PID_FILE="/tmp/${APP_NAME}.pid"
NODE_ENV="production"
DEV_MODE=${DEV_MODE:-true}

# Get configuration from Python
get_config() {
    source $VENV_PATH/bin/activate
    
    # Create config directory with correct permissions
    sudo mkdir -p /home/radio/radio/web/src/lib
    sudo chown -R radio:radio /home/radio/radio/web
    
    # Get configuration values
    API_PORT=$(python3 -c "from config.config import settings; print(settings.API_PORT)" 2>/dev/null || echo 80)
    DEV_PORT=$(python3 -c "from config.config import settings; print(settings.DEV_PORT)" 2>/dev/null || echo 5173)
    HOSTNAME=$(python3 -c "from config.config import settings; print(settings.HOSTNAME)" 2>/dev/null || echo "radiod")
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
    echo "Cleaning up any remaining processes..."
    sudo pkill -f "uvicorn.*$APP_PATH" || true
    pkill -f "npm run dev" || true
    pkill -f "vite" || true
    
    # Wait for ports to be freed
    sleep 3
    
    # Verify ports are free
    if [ -n "$DEV_PORT" ] && [ -n "$API_PORT" ]; then
        if lsof -ti :$DEV_PORT 2>/dev/null || sudo lsof -ti :$API_PORT 2>/dev/null; then
            echo "Error: Ports still in use after cleanup"
            exit 1
        fi
    fi
}

check_pigpiod() {
    if ! pgrep -x "pigpiod" > /dev/null; then
        echo "Starting pigpiod..."
        sudo systemctl start pigpiod
    else
        echo "pigpiod is already running."
    fi
}

check_nmcli_permissions() {
    # Create sudo rule for nmcli if it doesn't exist
    SUDO_FILE="/etc/sudoers.d/radio-nmcli"
    if [ ! -f "$SUDO_FILE" ]; then
        echo "Setting up nmcli and system permissions..."
        sudo tee $SUDO_FILE <<EOF
# Allow radio user to run specific nmcli commands without password
radio ALL=(ALL) NOPASSWD: /usr/bin/nmcli device wifi list
radio ALL=(ALL) NOPASSWD: /usr/bin/nmcli device wifi rescan
radio ALL=(ALL) NOPASSWD: /usr/bin/nmcli networking connectivity check
radio ALL=(ALL) NOPASSWD: /usr/bin/nmcli device wifi connect *
radio ALL=(ALL) NOPASSWD: /usr/bin/nmcli connection up *
radio ALL=(ALL) NOPASSWD: /usr/bin/nmcli connection delete *
radio ALL=(ALL) NOPASSWD: /usr/bin/nmcli connection show
radio ALL=(ALL) NOPASSWD: /usr/bin/nmcli device set *
radio ALL=(ALL) NOPASSWD: /usr/bin/nmcli connection add *
radio ALL=(ALL) NOPASSWD: /usr/bin/nmcli connection modify *
radio ALL=(ALL) NOPASSWD: /usr/bin/nmcli radio wifi *
radio ALL=(ALL) NOPASSWD: /usr/bin/nmcli networking *
radio ALL=(ALL) NOPASSWD: /usr/bin/rfkill
radio ALL=(ALL) NOPASSWD: /sbin/ip link set *
radio ALL=(ALL) NOPASSWD: /usr/bin/nmcli device disconnect *
# Add system control permissions
radio ALL=(ALL) NOPASSWD: /sbin/reboot
radio ALL=(ALL) NOPASSWD: /sbin/shutdown
EOF
        sudo chmod 440 $SUDO_FILE
    fi
}

ensure_client_mode() {
    echo "Ensuring client mode on startup..."
    source $VENV_PATH/bin/activate
    
    # Ensure correct permissions before running Python
    sudo chown -R radio:radio /home/radio/radio/web
    
    # Create directory and initial mode file if it doesn't exist
    echo "Setting up mode state file..."
    sudo mkdir -p /tmp/radio
    if [ ! -f "/tmp/radio/radio_mode.json" ]; then
        echo "Creating initial mode state file..."
        echo '{"mode": "CLIENT"}' | sudo tee /tmp/radio/radio_mode.json > /dev/null
    fi
    
    # Ensure correct permissions
    sudo chown -R radio:radio /tmp/radio
    sudo chmod 644 /tmp/radio/radio_mode.json
    
    # Add debug output
    echo "Running mode check and switch..."
    python3 -c "
from src.core.mode_manager import ModeManagerSingleton
import asyncio
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('mode_switch')

async def ensure_client():
    try:
        manager = ModeManagerSingleton.get_instance()
        await manager.enable_client_mode()  # This method already calls _save_state internally
        logger.info('Client mode switch completed')
            
    except Exception as e:
        logger.error(f'Error in mode switch: {str(e)}', exc_info=True)

asyncio.run(ensure_client())
"
    
    # Wait for network to be ready
    echo "Waiting for network..."
    max_attempts=30
    attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if sudo nmcli networking connectivity check | grep -q "full"; then
            echo "Network is ready"
            break
        fi
        echo "Waiting for network... attempt $((attempt+1))/$max_attempts"
        attempt=$((attempt+1))
        sleep 1
    done
    
    if [ $attempt -eq $max_attempts ]; then
        echo "Warning: Network not ready after $max_attempts attempts"
    fi
}

check_avahi() {
    echo "Checking Avahi daemon..."
    get_config
    
    # Install avahi-daemon if not present
    if ! command -v avahi-daemon &> /dev/null; then
        echo "Installing avahi-daemon..."
        sudo apt-get update
        sudo apt-get install -y avahi-daemon
    fi
    
    # Configure Avahi with hostname
    echo "Configuring Avahi..."
    sudo tee /etc/avahi/avahi-daemon.conf << EOF
[server]
host-name=$HOSTNAME
domain-name=local
use-ipv4=yes
use-ipv6=no
enable-dbus=yes
allow-interfaces=wlan0

[publish]
publish-addresses=yes
publish-hinfo=yes
publish-workstation=yes
publish-domain=yes
EOF
    
    # Restart Avahi daemon
    echo "Restarting Avahi daemon..."
    sudo systemctl restart avahi-daemon
    
    # Wait for Avahi to be ready
    sleep 2
    
    # Verify Avahi is running
    if ! systemctl is-active --quiet avahi-daemon; then
        echo "Warning: avahi-daemon is not running"
    else
        echo "avahi-daemon is running"
    fi
}

open_monitor() {
    echo "Opening monitor website..."
    
    # Check if X server is running
    if ! xset q &>/dev/null; then
        echo "X server not running, skipping monitor display"
        return
    fi
    
    # Kill any existing Chromium instances
    pkill -f chromium || true
    
    # Set display settings
    export DISPLAY=:0
    
    # Launch Chromium in kiosk mode
    nohup chromium-browser \
        --kiosk \
        --disable-restore-session-state \
        --noerrdialogs \
        --disable-session-crashed-bubble \
        --disable-infobars \
        --start-maximized \
        "http://$HOSTNAME.local:$DEV_PORT/monitor" &
}

start() {
    echo "Starting $APP_NAME..."
    get_config
    
    # Validate port values
    if [ -z "$API_PORT" ] || [ -z "$DEV_PORT" ]; then
        echo "Error: Invalid port configuration"
        exit 1
    fi
    
    echo "Using ports: API=$API_PORT, DEV=$DEV_PORT"
    
    # Check if already running
    if [ -f $PID_FILE ]; then
        echo "$APP_NAME is already running."
        exit 1
    fi
    
    # Create log directory if it doesn't exist
    mkdir -p $(dirname $LOG_FILE)
    WEB_LOG_FILE="${LOG_FILE%.*}_web.log"
    
    # Clean up any existing processes and ports
    check_ports
    
    # Add check_avahi to the startup sequence
    check_pigpiod
    check_avahi
    check_nmcli_permissions
    ensure_client_mode
    
    # Start FastAPI server
    echo "Starting FastAPI server on port $API_PORT..."
    if [ "$DEV_MODE" = true ]; then
        nohup sudo -E env "PATH=$PATH" \
            "PYTHONPATH=/home/radio/radio" \
            "$VENV_PATH/bin/uvicorn" src.api.main:app \
            --reload \
            --host "0.0.0.0" \
            --port "$API_PORT" \
            > $LOG_FILE 2>&1 &
    else
        nohup sudo -E env "PATH=$PATH" \
            "PYTHONPATH=/home/radio/radio" \
            "$VENV_PATH/bin/uvicorn" src.api.main:app \
            --host "0.0.0.0" \
            --port "$API_PORT" \
            > $LOG_FILE 2>&1 &
    fi
    API_PID=$!
    echo $API_PID > $PID_FILE
    
    sleep 3
    
    # Start web server based on mode
    echo "Starting web server on port $DEV_PORT..."
    
    # Change to web directory as radio user
    cd /home/radio/radio/web
    if [ "$DEV_MODE" = true ]; then
        echo "Starting in development mode..."
        sudo -u radio NODE_ENV=development \
            HOME=/home/radio \
            npm run dev -- \
            --host "0.0.0.0" \
            --port "$DEV_PORT" \
            >> "$WEB_LOG_FILE" 2>&1 &
    else
        echo "Starting in production mode..."
        sudo -u radio NODE_ENV=production \
            HOME=/home/radio \
            bash -c "npm run build && npm run preview -- \
            --host \"0.0.0.0\" \
            --port \"$DEV_PORT\"" \
            >> "$WEB_LOG_FILE" 2>&1 &
    fi
    DEV_PID=$!
    echo $DEV_PID >> $PID_FILE
    cd - # Return to original directory
    
    echo "$APP_NAME started successfully"
    echo "FastAPI PID: $API_PID"
    echo "Dev Server PID: $DEV_PID"
    
    # Show initial log entries
    echo "Initial log entries:"
    tail -n 5 $LOG_FILE
    
    # Open monitor page if in production mode
    if [ "$DEV_MODE" = false ]; then
        open_monitor
    fi
}

stop() {
    if [ -f $PID_FILE ]; then
        while read PID; do
            echo "Stopping process with PID $PID..."
            sudo kill -15 $PID 2>/dev/null || true
            sleep 2
            # Force kill if still running
            sudo kill -9 $PID 2>/dev/null || true
        done < $PID_FILE
        rm -f $PID_FILE
        echo "$APP_NAME stopped."
        
        # Kill any remaining processes
        sudo pkill -f "uvicorn.*$APP_PATH"
        pkill -f "npm run dev"
    else
        echo "$APP_NAME is not running."
    fi
    
    # Double check ports are free
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