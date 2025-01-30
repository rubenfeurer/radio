#!/bin/bash

APP_NAME="radio"
VENV_PATH="/home/radio/radio/venv"
APP_PATH="/home/radio/radio/src/api/main.py"
LOG_FILE="/home/radio/radio/logs/radio.log"
WEB_LOG_FILE="/home/radio/radio/logs/web.log"
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

    # Check dnsmasq configuration
    if [ ! -f "/etc/dnsmasq.conf" ]; then
        echo "Error: dnsmasq configuration not found"
        exit 1
    fi

    # Check and start required services with NOPASSWD sudo
    for service in avahi-daemon dnsmasq NetworkManager pigpiod; do
        echo "Starting $service..."
        sudo systemctl start $service || {
            echo "Warning: Could not start $service, attempting to install..."
            sudo apt-get install -y $service
            sudo systemctl start $service || echo "Warning: Could not start $service"
        }
    done

    # Verify MPV installation with correct path
    if ! ldconfig -p | grep libmpv > /dev/null; then
        echo "Error: libmpv not found in system library path"
        # Try to fix MPV symlinks
        sudo ln -sf /usr/lib/aarch64-linux-gnu/libmpv.so.2 /usr/lib/libmpv.so
        sudo ldconfig
        if ! ldconfig -p | grep libmpv > /dev/null; then
            exit 1
        fi
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

    # Get current IP address dynamically
    WIFI_IP=$(ip -4 addr show wlan0 | grep -oP '(?<=inet\s)\d+(\.\d+){3}')

    # Configure hosts file first
    echo "Configuring hosts file..."
    sudo tee /etc/hosts > /dev/null << EOF
127.0.0.1       localhost
::1             localhost ip6-localhost ip6-loopback
ff02::1         ip6-allnodes
ff02::2         ip6-allrouters
127.0.1.1       radiod
${WIFI_IP}      radiod.local
EOF

    # Configure dnsmasq with dynamic IP
    echo "Configuring dnsmasq..."
    sudo tee /etc/dnsmasq.conf > /dev/null << EOF
interface=wlan0
domain-needed
bogus-priv
expand-hosts
domain=local
local=/local/
listen-address=127.0.0.1,${WIFI_IP}
address=/radiod.local/${WIFI_IP}
bind-interfaces
except-interface=docker0
EOF

    # Configure avahi for dynamic setup
    echo "Configuring avahi-daemon..."
    sudo tee /etc/avahi/avahi-daemon.conf > /dev/null << EOF
[server]
host-name=radiod
domain-name=local
use-ipv4=yes
use-ipv6=no
allow-interfaces=wlan0
enable-dbus=yes
publish-addresses=yes

[publish]
publish-addresses=yes
publish-hinfo=yes
publish-workstation=yes
publish-domain=yes

[wide-area]
enable-wide-area=yes
EOF

    # Start services in correct order
    echo "Starting network services..."

    # Restart services in proper order
    for service in wpa_supplicant NetworkManager dnsmasq avahi-daemon; do
        echo "Restarting $service..."
        sudo systemctl restart $service
        sleep 2
    done

    # Wait for IP address assignment and update configs if needed
    echo "Waiting for IP address assignment..."
    for i in {1..30}; do
        NEW_IP=$(ip -4 addr show wlan0 2>/dev/null | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
        if [ -n "$NEW_IP" ] && [ "$NEW_IP" != "$WIFI_IP" ]; then
            echo "IP address changed to: $NEW_IP"
            # Update hosts file
            sudo sed -i "s/${WIFI_IP}.*radiod.local/${NEW_IP}      radiod.local/" /etc/hosts
            # Update dnsmasq config
            sudo sed -i "s/listen-address=.*/listen-address=127.0.0.1,${NEW_IP}/" /etc/dnsmasq.conf
            sudo sed -i "s/address=\/radiod.local\/.*/address=\/radiod.local\/${NEW_IP}/" /etc/dnsmasq.conf
            # Restart dnsmasq to apply changes
            sudo systemctl restart dnsmasq
            break
        fi
        sleep 1
    done
}

setup_system() {
    echo "Setting up system dependencies..."

    # Create required directories
    sudo mkdir -p /home/radio/radio/logs
    sudo chown -R radio:radio /home/radio/radio/logs

    # Install system packages with proper package names for Raspberry Pi OS
    sudo apt-get update
    sudo apt-get install -y \
        mpv \
        libmpv2 \
        libmpv-dev \
        dnsmasq \
        network-manager \
        wireless-tools \
        wpasupplicant \
        firmware-brcm80211

    # Create symlink for libmpv with correct path for Raspberry Pi OS
    sudo ln -sf /usr/lib/aarch64-linux-gnu/libmpv.so.2 /usr/lib/libmpv.so
    sudo ln -sf /usr/lib/aarch64-linux-gnu/libmpv.so.2 /usr/local/lib/libmpv.so
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

start_web_server() {
    if [ "$DEV_MODE" = true ]; then
        echo "Starting web server in development mode on port $DEV_PORT..."

        # Ensure we're in the web directory
        cd /home/radio/radio/web || exit 1

        # Clean install if needed
        if [ ! -d "node_modules" ]; then
            echo "Installing npm dependencies..."
            npm install
        fi

        # Start the dev server with explicit environment variables
        sudo -E -u radio \
            PATH="/home/radio/.nvm/versions/node/v22.13.1/bin:$PATH" \
            NODE_ENV=development \
            PORT=$DEV_PORT \
            HOST=0.0.0.0 \
            HOME=/home/radio \
            /home/radio/.nvm/versions/node/v22.13.1/bin/npm run dev -- \
            --host "0.0.0.0" \
            --port "$DEV_PORT" \
            --strictPort \
            >> "$WEB_LOG_FILE" 2>&1 &

        # Store PID
        WEB_PID=$!
        echo $WEB_PID >> $PID_FILE

        # Return to original directory
        cd - || exit 1

        # Wait for server to start
        echo "Waiting for web server to start..."
        for i in {1..30}; do
            if curl -s "http://localhost:$DEV_PORT" >/dev/null; then
                echo "Web server started successfully on port $DEV_PORT"
                return 0
            fi
            sleep 1
        done

        echo "Error: Web server failed to start"
        tail -n 20 "$WEB_LOG_FILE"
        return 1
    fi
}

start_api_server() {
    echo "Starting API server..."

    # Activate virtual environment and start uvicorn
    source "$VENV_PATH/bin/activate"

    # Start the API server with nohup
    nohup "$VENV_PATH/bin/python" -m uvicorn \
        src.api.main:app \
        --host "0.0.0.0" \
        --port "$API_PORT" \
        --reload \
        >> "$LOG_FILE" 2>&1 &

    API_PID=$!
    echo $API_PID >> $PID_FILE

    # Wait for API server to start
    echo "Waiting for API server to start..."
    for i in {1..30}; do
        if curl -s "http://localhost:$API_PORT/api/v1/health" >/dev/null; then
            echo "API server started successfully on port $API_PORT"
            return 0
        fi
        sleep 1
    done

    echo "Error: API server failed to start"
    tail -n 20 "$LOG_FILE"
    return 1
}

start() {
    echo "Starting $APP_NAME..."
    get_config
    validate_network
    validate_installation
    ensure_client_mode
    check_ports

    # Start the API server first
    start_api_server || exit 1

    # Then start the web server
    start_web_server || exit 1

    echo "$APP_NAME started successfully"
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
