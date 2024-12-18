#!/bin/bash

APP_NAME="radio"
VENV_PATH="/home/radio/radio/venv"
APP_PATH="/home/radio/radio/src/api/main.py"
LOG_FILE="/home/radio/radio/logs/radio.log"
PID_FILE="/tmp/${APP_NAME}.pid"
NODE_ENV="production"

# Get port numbers from Python config
get_ports() {
    source $VENV_PATH/bin/activate
    API_PORT=$(python3 -c "from config.config import settings; print(settings.API_PORT)")
    DEV_PORT=$(python3 -c "from config.config import settings; print(settings.DEV_PORT)")
}

check_ports() {
    get_ports
    
    # Check and kill any existing processes on API_PORT
    if sudo lsof -Pi :$API_PORT -sTCP:LISTEN -t >/dev/null ; then
        echo "Port $API_PORT is already in use. Stopping existing process..."
        sudo kill -9 $(sudo lsof -t -i:$API_PORT)
        sleep 2
    fi
    
    # Check and kill any existing processes on DEV_PORT
    if lsof -Pi :$DEV_PORT -sTCP:LISTEN -t >/dev/null ; then
        echo "Port $DEV_PORT is already in use. Stopping existing process..."
        sudo kill -9 $(lsof -t -i:$DEV_PORT)
        sleep 2
    fi

    # Additional check for any hanging processes
    sudo pkill -f "uvicorn.*$APP_PATH" || true
    pkill -f "npm run dev" || true
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
        echo "Setting up nmcli permissions..."
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
radio ALL=(ALL) NOPASSWD: /usr/bin/rfkill
radio ALL=(ALL) NOPASSWD: /sbin/ip link set *
radio ALL=(ALL) NOPASSWD: /usr/bin/nmcli device disconnect *
radio ALL=(ALL) NOPASSWD: /usr/bin/nmcli radio wifi *
EOF
        sudo chmod 440 $SUDO_FILE
    fi
}

ensure_client_mode() {
    echo "Ensuring client mode on startup..."
    source $VENV_PATH/bin/activate
    
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
        if nmcli networking connectivity check | grep -q "full"; then
            echo "Network is ready"
            break
        fi
        echo "Waiting for network... attempt $((attempt+1))/$max_attempts"
        sleep 2
        attempt=$((attempt+1))
    done
    
    if [ $attempt -eq $max_attempts ]; then
        echo "Warning: Network connection timed out. Continuing anyway..."
    fi
    
    # Verify network interface is up
    if ! ip link show wlan0 | grep -q "UP"; then
        echo "Bringing up wlan0 interface..."
        sudo ip link set wlan0 up
    fi
}

open_monitor() {
    echo "Opening monitor website..."
    # Wait for services to be fully up
    sleep 5
    
    # Check if Chromium is already running with monitor page
    if ! pgrep -f "chromium.*monitor" > /dev/null; then
        # Kill any existing Chromium instances first
        pkill chromium 2>/dev/null || true
        sleep 1
        
        # Open Chromium with proper flags
        DISPLAY=:0 chromium-browser \
            --kiosk \
            --start-fullscreen \
            --disable-restore-session-state \
            --noerrdialogs \
            --disable-session-crashed-bubble \
            --no-first-run \
            "http://localhost:$DEV_PORT/monitor" > /dev/null 2>&1 &
    else
        echo "Monitor already open in browser"
    fi
}

check_network_manager() {
    echo "Checking NetworkManager status..."
    if ! systemctl is-active --quiet NetworkManager; then
        echo "NetworkManager is not running. Starting it..."
        sudo systemctl start NetworkManager
        # Wait for NetworkManager to be fully up
        sleep 5
        if systemctl is-active --quiet NetworkManager; then
            echo "NetworkManager started successfully"
        else
            echo "Failed to start NetworkManager"
            exit 1
        fi
    else
        echo "NetworkManager is running"
    fi
}

check_hostapd() {
    echo "Checking hostapd status..."
    
    if systemctl is-active --quiet hostapd; then
        echo "Stopping hostapd..."
        sudo systemctl stop hostapd
        sudo systemctl disable hostapd
        
        # Force kill any remaining hostapd processes
        sudo pkill -9 hostapd || true
        sleep 2
        
        # Double check it's really stopped
        if systemctl is-active --quiet hostapd; then
            echo "Warning: hostapd is still running!"
        else
            echo "hostapd stopped successfully"
        fi
    else
        echo "hostapd is already stopped"
    fi
}

setup_network_manager_config() {
    echo "Setting up NetworkManager configuration..."
    
    # Create NetworkManager config file
    sudo tee /etc/NetworkManager/conf.d/10-wifi.conf << EOF
[main]
plugins=ifupdown,keyfile
no-auto-default=*

[ifupdown]
managed=true

[device]
wifi.scan-rand-mac-address=no
wifi.backend=wpa_supplicant

[connection]
wifi.powersave=0
connection.autoconnect=true

[logging]
level=DEBUG
domains=WIFI,CORE,DEVICE
EOF

    # Set correct permissions
    sudo chmod 644 /etc/NetworkManager/conf.d/10-wifi.conf
    
    # Restart NetworkManager to apply changes
    echo "Restarting NetworkManager to apply changes..."
    sudo systemctl restart NetworkManager
    sleep 5
}

setup_wifi_interface() {
    echo "Setting up WiFi interface..."
    
    # Unblock WiFi if blocked
    echo "Checking RF kill status..."
    sudo rfkill unblock wifi
    
    # Reset interface
    echo "Resetting WiFi interface..."
    sudo ip link set wlan0 down
    sleep 1
    
    # Set to managed mode
    echo "Setting managed mode..."
    sudo nmcli device set wlan0 managed yes
    sleep 1
    
    # Bring interface up
    echo "Bringing up interface..."
    sudo ip link set wlan0 up
    sleep 2
    
    # Verify interface status
    if ip link show wlan0 | grep -q "UP"; then
        echo "WiFi interface is up"
    else
        echo "Warning: Failed to bring up WiFi interface"
    fi
}

start() {
    echo "Starting $APP_NAME..."
    check_ports
    check_pigpiod
    check_network_manager
    setup_network_manager_config
    check_hostapd
    setup_wifi_interface
    check_nmcli_permissions
    ensure_client_mode
    source $VENV_PATH/bin/activate
    echo "Virtual environment activated"
    
    # Clear the log file
    echo "" > $LOG_FILE
    
    # Ensure /tmp/radio directory exists with correct permissions
    echo "Setting up temporary directory with correct permissions..."
    sudo mkdir -p /tmp/radio
    sudo chown -R radio:radio /tmp/radio
    
    # Start FastAPI server with nohup
    echo "Starting FastAPI server on port $API_PORT..."
    nohup sudo -E env "PATH=$PATH" \
        "PYTHONPATH=/home/radio/radio" \
        "TMPDIR=/tmp/radio" \
        "$VENV_PATH/bin/uvicorn" src.api.main:app \
        --host 0.0.0.0 \
        --port "$API_PORT" \
        --reload \
        --log-level debug > $LOG_FILE 2>&1 &
    API_PID=$!
    echo $API_PID > $PID_FILE
    
    # Wait to ensure API server is up
    sleep 5
    
    # Ensure correct permissions for created files
    sudo chown -R radio:radio /tmp/radio
    
    # Start development server with nohup
    echo "Starting development server on port $DEV_PORT..."
    cd web && nohup npm run dev -- \
        --host "0.0.0.0" \
        --port "$DEV_PORT" \
        >> $LOG_FILE 2>&1 &
    DEV_PID=$!
    echo $DEV_PID >> $PID_FILE
    
    # Wait to ensure both servers start
    sleep 3
    
    # Check if processes are running
    if ps -p $API_PID > /dev/null && ps -p $DEV_PID > /dev/null; then
        echo "$APP_NAME started successfully"
        echo "FastAPI PID: $API_PID"
        echo "Dev Server PID: $DEV_PID"
        echo "Initial log entries:"
        tail -n 10 $LOG_FILE
        
        # Open monitor website
        open_monitor
    else
        echo "Failed to start $APP_NAME. Check logs for details."
        cat $LOG_FILE
        rm -f $PID_FILE
        exit 1
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
    get_ports
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