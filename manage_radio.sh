#!/bin/bash

APP_NAME="radio"
VENV_PATH="/home/radio/radio/venv"
APP_PATH="/home/radio/radio/src/api/main.py"
LOG_FILE="/home/radio/radio/logs/radio.log"
PID_FILE="/tmp/${APP_NAME}.pid"
NODE_ENV="production"
DEV_MODE=${DEV_MODE:-true}  # Changed default to true

# Get port numbers from Python config
get_ports() {
    source $VENV_PATH/bin/activate
    API_PORT=$(python3 -c "from config.config import settings; print(settings.API_PORT)")
    DEV_PORT=$(python3 -c "from config.config import settings; print(settings.DEV_PORT)")
}

check_ports() {
    get_ports
    
    echo "Checking for processes using ports..."
    
    # More thorough port check for DEV_PORT (5173)
    for pid in $(lsof -ti:$DEV_PORT); do
        echo "Killing process $pid using port $DEV_PORT..."
        sudo kill -9 $pid 2>/dev/null || true
    done
    
    # More thorough port check for API_PORT (80)
    for pid in $(sudo lsof -ti:$API_PORT); do
        echo "Killing process $pid using port $API_PORT..."
        sudo kill -9 $pid 2>/dev/null || true
    done

    # Additional cleanup
    echo "Cleaning up any remaining processes..."
    sudo pkill -f "uvicorn.*$APP_PATH" || true
    pkill -f "npm run dev" || true
    pkill -f "vite" || true
    
    # Wait for ports to be freed
    sleep 3
    
    # Verify ports are free
    if lsof -Pi:$DEV_PORT -sTCP:LISTEN || sudo lsof -Pi:$API_PORT -sTCP:LISTEN; then
        echo "Error: Ports still in use after cleanup"
        exit 1
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
    
    # Check if Chromium is already running
    if ! pgrep -f "chromium.*monitor" > /dev/null; then
        # Kill any existing Chromium instances first
        pkill chromium 2>/dev/null || true
        pkill chromium-browser 2>/dev/null || true
        sleep 2
        
        # Set display for Pi
        export DISPLAY=:0
        
        # Disable screen blanking
        xset s off
        xset -dpms
        xset s noblank
        
        # Open Chromium with proper flags for Pi
        DISPLAY=:0 chromium-browser \
            --noerrdialogs \
            --disable-infobars \
            --disable-session-crashed-bubble \
            --disable-translate \
            --disable-restore-session-state \
            --disable-sync \
            --disable-features=TranslateUI \
            --disable-gpu \
            --start-maximized \
            --kiosk \
            --no-first-run \
            --incognito \
            --user-data-dir=/home/radio/.config/chromium-monitor \
            "http://localhost:$DEV_PORT/monitor" > /dev/null 2>&1 &
            
        echo "Monitor page opened in kiosk mode"
    else
        echo "Monitor already open in browser"
    fi
    
    # Verify browser launched
    sleep 3
    if ! pgrep -f "chromium.*monitor" > /dev/null; then
        echo "Warning: Failed to open monitor page"
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
    
    # Stop and disable potentially conflicting services
    echo "Handling conflicting services..."
    local services=("hostapd" "iwd" "dhcpcd")
    for service in "${services[@]}"; do
        if systemctl list-unit-files | grep -q "^$service"; then
            echo "Handling $service..."
            sudo systemctl stop $service 2>/dev/null || true
            sudo systemctl disable $service 2>/dev/null || true
        fi
    done

    # Explicitly configure wpa_supplicant without stopping it
    echo "Configuring wpa_supplicant..."
    sudo systemctl unmask wpa_supplicant
    sudo systemctl enable wpa_supplicant
    
    # Create NetworkManager config file
    echo "Creating NetworkManager configuration..."
    sudo tee /etc/NetworkManager/conf.d/10-wifi.conf << EOF
[main]
plugins=ifupdown,keyfile
no-auto-default=*
dhcp=internal

[ifupdown]
managed=true

[device]
wifi.scan-rand-mac-address=no
wifi.backend=wpa_supplicant

[connection]
wifi.powersave=0
connection.autoconnect=true
ipv6.method=disabled

[logging]
level=DEBUG
domains=WIFI,CORE,DEVICE,SUPPLICANT
EOF

    # Set correct permissions
    sudo chmod 644 /etc/NetworkManager/conf.d/10-wifi.conf
    
    # Reload NetworkManager config without stopping the service
    echo "Reloading NetworkManager configuration..."
    sudo systemctl reload NetworkManager || sudo systemctl restart NetworkManager
    sleep 2

    # Verify services
    echo "Verifying services..."
    if ! systemctl is-active --quiet wpa_supplicant; then
        echo "Warning: wpa_supplicant is not running, starting it..."
        sudo systemctl start wpa_supplicant
    fi
    
    if ! systemctl is-active --quiet NetworkManager; then
        echo "Warning: NetworkManager is not running, starting it..."
        sudo systemctl start NetworkManager
    fi
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

check_avahi() {
    echo "Checking Avahi daemon..."
    
    # Get system hostname
    HOSTNAME=$(hostname)
    echo "Using hostname: $HOSTNAME"
    
    # Install avahi-daemon if not present
    if ! dpkg -l | grep -q avahi-daemon; then
        echo "Installing avahi-daemon..."
        sudo apt-get update
        sudo apt-get install -y avahi-daemon
    fi
    
    # Configure Avahi
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
    
    # Verify Avahi is running
    if ! systemctl is-active --quiet avahi-daemon; then
        echo "Error: Avahi daemon failed to start"
        sudo systemctl status avahi-daemon
        exit 1
    else
        echo "Avahi daemon is running"
    fi
    
    # Test hostname resolution
    echo "Testing hostname resolution..."
    if ! ping -c 1 $HOSTNAME.local > /dev/null 2>&1; then
        echo "Warning: $HOSTNAME.local is not resolving. Check your network configuration."
    else
        echo "Hostname resolution successful"
    fi
}

setup_logrotate() {
    echo "Setting up log rotation..."
    
    # Create logrotate configuration
    sudo tee /etc/logrotate.d/radio << EOF
/home/radio/radio/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 radio radio
    size 10M
    postrotate
        systemctl restart radio >/dev/null 2>&1 || true
    endscript
}
EOF

    # Set correct permissions
    sudo chmod 644 /etc/logrotate.d/radio
    
    # Force logrotate to read the new config
    sudo logrotate -f /etc/logrotate.d/radio
}

start() {
    echo "Starting $APP_NAME in ${DEV_MODE} mode..."
    
    # Setup log rotation before starting services
    setup_logrotate
    
    # Create logs directory if it doesn't exist
    mkdir -p "$(dirname $LOG_FILE)"
    sudo chown -R radio:radio "$(dirname $LOG_FILE)"
    
    # Create web logs directory with proper permissions
    WEB_LOG_FILE="/home/radio/radio/logs/web.log"
    mkdir -p "$(dirname $WEB_LOG_FILE)"
    sudo chown -R radio:radio "$(dirname $WEB_LOG_FILE)"
    
    # Ensure web directory permissions
    sudo chown -R radio:radio /home/radio/radio/web
    
    # Add check_avahi to the startup sequence
    check_pigpiod
    check_network_manager
    check_avahi
    setup_network_manager_config
    check_hostapd
    setup_wifi_interface
    check_nmcli_permissions
    ensure_client_mode
    
    # Create and set permissions for temp directory
    echo "Setting up temporary directory with correct permissions..."
    sudo mkdir -p /tmp/radio
    sudo chown -R radio:radio /tmp/radio
    export TMPDIR=/tmp/radio
    
    # Activate virtual environment
    echo "Virtual environment activated"
    source $VENV_PATH/bin/activate
    
    # Check and kill any existing processes
    check_ports
    
    # Start FastAPI server with nohup
    echo "Starting FastAPI server on port $API_PORT..."
    if [ "$DEV_MODE" = true ]; then
        nohup sudo -E env "PATH=$PATH" \
            "PYTHONPATH=/home/radio/radio" \
            "$VENV_PATH/bin/uvicorn" src.api.main:app \
            --host "0.0.0.0" \
            --port "$API_PORT" \
            --reload \
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