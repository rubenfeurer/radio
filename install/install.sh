#!/bin/bash

# Exit on error
set -e

echo "Starting Internet Radio installation..."

# Configuration
RADIO_USER="radio"
RADIO_HOME="/home/${RADIO_USER}/radio"
VENV_PATH="${RADIO_HOME}/venv"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root"
    exit 1
fi

echo "1. Installing system dependencies..."
apt-get update
apt-get install -y \
    python3-venv \
    python3-pip \
    mpv \
    pigpio \
    pulseaudio \
    avahi-daemon \
    python3-dev \
    build-essential \
    libssl-dev \
    libffi-dev

# Start and enable pigpiod
echo "2. Setting up pigpiod service..."
systemctl enable pigpiod
systemctl start pigpiod

echo "3. Creating radio user..."
# Create radio user if not exists
if ! id "${RADIO_USER}" &>/dev/null; then
    useradd -m ${RADIO_USER}
    usermod -a -G audio,gpio,pulse-access ${RADIO_USER}
fi

echo "4. Setting up application directory..."
# Create application directory
mkdir -p ${RADIO_HOME}/{logs,config}
cp -r * ${RADIO_HOME}/
chown -R ${RADIO_USER}:${RADIO_USER} ${RADIO_HOME}

echo "5. Setting up Python virtual environment..."
# Create and activate virtual environment
sudo -u ${RADIO_USER} bash << EOF
python3 -m venv ${VENV_PATH}
source ${VENV_PATH}/bin/activate
pip install --upgrade pip
pip install -r ${RADIO_HOME}/requirements.txt
EOF

echo "6. Setting up system service..."
# Install systemd service
cp install/radio.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable radio

echo "7. Setting up audio..."
# Configure audio permissions
usermod -a -G audio ${RADIO_USER}
mkdir -p /run/user/1000/pulse
chown -R ${RADIO_USER}:${RADIO_USER} /run/user/1000/pulse

echo "8. Starting radio service..."
systemctl start radio

# Wait for service to start
sleep 5

# Check if service is running
if systemctl is-active --quiet radio; then
    echo "✓ Installation successful!"
    echo "Access your radio at: http://radiod.local"
    echo "If radiod.local doesn't work, find your IP with: hostname -I"
else
    echo "! Service failed to start. Check logs with: journalctl -u radio -f"
    exit 1
fi

# Print helpful information
echo
echo "Useful commands:"
echo "- View logs: sudo journalctl -u radio -f"
echo "- Restart radio: sudo systemctl restart radio"
echo "- Check status: sudo systemctl status radio"
echo
echo "Default AP mode:"
echo "- SSID: RadioPi"
echo "- Password: Check config/settings.json" 