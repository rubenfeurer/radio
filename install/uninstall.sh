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
systemctl stop pigpiod || true
systemctl disable pigpiod || true

# Remove systemd service files
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

# Clean up network configurations
echo "Cleaning up network configurations..."
# Remove network configurations
rm -f /etc/default/crda
rm -f /etc/hostapd/hostapd.conf
rm -f /etc/sudoers.d/radio-nmcli

# Reset Avahi configuration
echo "Resetting Avahi configuration..."
rm -f /etc/avahi/avahi-daemon.conf
systemctl restart avahi-daemon || true

# Clean up directories
echo "Cleaning up directories..."
rm -rf /tmp/mpv-socket
rm -rf /tmp/radio
rm -rf /run/user/1000/pulse

# Remove dependencies (ask for confirmation)
read -p "Do you want to remove installed dependencies? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Removing dependencies..."
    
    # Remove system dependencies from file
    while read -r line; do
        # Skip comments and empty lines
        [[ $line =~ ^#.*$ ]] && continue
        [[ -z $line ]] && continue
        
        echo "Removing $line..."
        apt-get remove -y $line
    done < system-requirements.txt
    
    echo "Cleaning up unused packages..."
    apt-get autoremove -y
fi

# Reset network if in AP mode
if systemctl is-active --quiet hostapd; then
    echo "Disabling Access Point mode..."
    systemctl stop hostapd
    systemctl disable hostapd
    nmcli connection delete Hotspot || true
fi

# Clean up system files
echo "Cleaning up system files..."
rm -rf /var/log/${SERVICE_NAME}

echo "Uninstallation complete!"
echo
echo "Note: System has been reset to its original state."
echo "The following changes were made:"
echo "- Removed radio user and home directory"
echo "- Removed all radio service files"
echo "- Cleaned up network configurations"
echo "- Reset audio settings"
echo "- Removed temporary files and directories"
echo "- Disabled and removed AP mode configuration"
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "- Removed all installed dependencies"
fi
echo
echo "A reboot is recommended to ensure all changes take effect."
echo "Would you like to reboot now? (y/N)"
read -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    reboot
fi 