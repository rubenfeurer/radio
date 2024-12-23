#!/bin/bash

# Exit on error
set -e

# Configuration
RADIO_USER="radio"
RADIO_HOME="/home/${RADIO_USER}/radio"
SERVICE_NAME="radio"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root"
    exit 1
fi

echo "Starting Radio uninstallation..."

# Stop and disable services
echo "Stopping and disabling services..."
systemctl stop ${SERVICE_NAME} || true
systemctl disable ${SERVICE_NAME} || true
rm -f /etc/systemd/system/${SERVICE_NAME}.service
systemctl daemon-reload

# Remove application files
echo "Removing application files..."
rm -rf ${RADIO_HOME}

# Remove radio user
echo "Removing radio user..."
pkill -u ${RADIO_USER} || true  # Kill any remaining processes
userdel -r ${RADIO_USER} || true  # Remove user and their home directory

# Reset audio
echo "Resetting audio configuration..."
systemctl restart pulseaudio || true

# Remove dependencies (ask for confirmation)
read -p "Do you want to remove installed dependencies? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Removing dependencies..."
    apt-get remove -y \
        python3-venv \
        pigpio \
        mpv || true
    
    echo "Cleaning up unused packages..."
    apt-get autoremove -y
fi

# Reset network if in AP mode
if systemctl is-active --quiet hostapd; then
    echo "Disabling Access Point mode..."
    systemctl stop hostapd
    systemctl disable hostapd
    rm -f /etc/hostapd/hostapd.conf
fi

# Clean up system files
echo "Cleaning up system files..."
rm -f /etc/systemd/system/${SERVICE_NAME}.service
rm -rf /var/log/${SERVICE_NAME}

echo "Uninstallation complete!"
echo
echo "Note: If you want to completely remove all configuration files,"
echo "you may also want to manually check these locations:"
echo "- /etc/systemd/system/ (for any remaining service files)"
echo "- /var/log/ (for any remaining log files)"
echo "- /etc/hostapd/ (for any remaining AP configuration)" 