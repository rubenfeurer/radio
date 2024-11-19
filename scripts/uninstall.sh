#!/bin/bash

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

echo "Starting uninstallation..."

# Stop and disable the service
systemctl stop radio
systemctl disable radio

# Remove service file
rm -f /etc/systemd/system/radio.service

# Remove sound configuration
rm -f /etc/asound.conf

# Remove log rotation configuration
rm -f /etc/logrotate.d/radio

# Remove sudoers configuration for nmcli
rm -f /etc/sudoers.d/radio-wifi

# Clean up Python packages (optional)
echo "Do you want to remove installed Python packages? (y/N)"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])+$ ]]; then
    pip3 uninstall -y -r requirements.txt
fi

# Clean up system packages (optional)
echo "Do you want to remove system packages? (y/N)"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])+$ ]]; then
    apt-get remove -y \
        vlc \
        alsa-utils \
        libasound2-dev \
        python3-vlc \
        python3-tomli \
        python3-tomli-w \
        network-manager
    apt-get autoremove -y
fi

# Clean up configuration and logs (optional)
echo "Do you want to remove configuration and log files? (y/N)"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])+$ ]]; then
    rm -rf /home/radio/internetRadio/logs/*
    rm -rf /home/radio/internetRadio/config/*
    rm -rf /home/radio/internetRadio/sounds/*
fi

# Remove radio user from groups (if not removing user)
echo "Do you want to remove the radio user from groups but keep the user? (y/N)"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])+$ ]]; then
    gpasswd -d radio audio
    gpasswd -d radio video
    gpasswd -d radio gpio
    gpasswd -d radio netdev
fi

# Remove radio user (optional)
echo "Do you want to remove the radio user? (y/N)"
read -r response
if [[ "$response" =~ ^([yY][eE][sS]|[yY])+$ ]]; then
    userdel -r radio
fi

# Reload systemd daemon
systemctl daemon-reload

echo "Uninstallation complete!" 