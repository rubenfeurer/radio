#!/bin/bash

VENV_PATH="/home/radio/radio/venv"

# Get configuration from Python
get_config() {
    source $VENV_PATH/bin/activate
    HOSTNAME=$(python3 -c "from config.config import settings; print(settings.HOSTNAME)")
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
wifi.powersave=2
EOF
}

# Main execution
echo "Starting network reset..."
get_config
check_network_manager
check_hostapd
setup_network_manager_config

# Reset WiFi interface
echo "Resetting WiFi interface..."
sudo rfkill unblock wifi
sudo ip link set wlan0 down
sleep 1
sudo nmcli device set wlan0 managed yes
sleep 1
sudo ip link set wlan0 up
sleep 2

echo "Network reset complete" 