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

# Skip if running in Docker
if [ -f /.dockerenv ]; then
    # Only run dependency installation in Docker
    echo "Running in Docker environment..."
    
    # Install system dependencies
    apt-get update
    while read -r line; do
        [[ $line =~ ^#.*$ ]] && continue
        [[ -z $line ]] && continue
        apt-get install -y $line
    done < install/system-requirements.txt
    
    # Install Python dependencies
    python3 -m venv ${VENV_PATH}
    source ${VENV_PATH}/bin/activate
    pip install --upgrade pip
    pip install -r install/requirements.txt
    
    exit 0
fi

# Regular installation continues here...

echo "1. Installing system dependencies..."
apt-get update

# Install system dependencies from file
while read -r line; do
    # Skip comments and empty lines
    [[ $line =~ ^#.*$ ]] && continue
    [[ -z $line ]] && continue
    
    echo "Installing $line..."
    apt-get install -y $line
done < system-requirements.txt

# Start and enable pigpiod
echo "2. Setting up pigpiod service..."
systemctl enable pigpiod
systemctl start pigpiod

echo "3. Creating radio user..."
# Create radio user if not exists
if ! id "${RADIO_USER}" &>/dev/null; then
    useradd -m ${RADIO_USER}
    # Add to all necessary groups for Raspberry Pi
    usermod -a -G audio,gpio,dialout,pulse-access,netdev ${RADIO_USER}
fi

echo "4. Setting up network permissions..."
# Configure nmcli permissions
SUDO_FILE="/etc/sudoers.d/radio-nmcli"
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

# Configure NetworkManager
echo "Configuring NetworkManager..."
sudo tee /etc/NetworkManager/NetworkManager.conf <<EOF
[main]
plugins=ifupdown,keyfile
dhcp=internal

[ifupdown]
managed=true

[device]
wifi.scan-rand-mac-address=no
EOF

# Restart NetworkManager to apply changes
systemctl restart NetworkManager

echo "5. Setting up Avahi daemon..."
# Configure Avahi for .local domain
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

echo "6. Setting up application directory..."
# Create required directories
mkdir -p ${RADIO_HOME}/{src,config,web,install,sounds,data,logs}

# Define required files and directories
REQUIRED_FILES=(
    "manage_radio.sh"
    "install/install.sh"
    "install/uninstall.sh"
    "install/requirements.txt"
    "install/system-requirements.txt"
    "install/reset_radio.sh"
    "config/config.py"
    "config/stations.json"
)

REQUIRED_DIRS=(
    "src/api"
    "src/core"
    "src/hardware"
    "src/system"
    "src/utils"
    "sounds"
    "web/build"
)

# Only copy files if we're not already in the target directory
if [ "$PWD" != "${RADIO_HOME}" ]; then
    echo "Copying files to ${RADIO_HOME}..."
    
    # Copy directories with verification
    for dir in "${REQUIRED_DIRS[@]}"; do
        if [ -d "$dir" ]; then
            echo "Copying directory: $dir"
            cp -r "$dir" "${RADIO_HOME}/${dir%/*}/"
        else
            echo "Warning: Required directory not found: $dir"
            exit 1
        fi
    done
    
    # Copy individual files with verification
    for file in "${REQUIRED_FILES[@]}"; do
        if [ -f "$file" ]; then
            echo "Copying file: $file"
            cp "$file" "${RADIO_HOME}/${file%/*}/"
        else
            # Skip optional files, exit on required ones
            case "$file" in
                "install/reset_radio.sh"|"LICENSE"|"README.md")
                    echo "Optional file not found: $file"
                    ;;
                *)
                    echo "Error: Required file not found: $file"
                    exit 1
                    ;;
            esac
        fi
    done
else
    echo "Already in installation directory, skipping file copy..."
fi

# Create empty directories and placeholder files
touch ${RADIO_HOME}/data/.keep
touch ${RADIO_HOME}/logs/.keep

# Set correct ownership
chown -R ${RADIO_USER}:${RADIO_USER} ${RADIO_HOME}

# Verify critical files
CRITICAL_FILES=(
    "${RADIO_HOME}/manage_radio.sh"
    "${RADIO_HOME}/install/requirements.txt"
    "${RADIO_HOME}/install/system-requirements.txt"
    "${RADIO_HOME}/config/config.py"
)

for file in "${CRITICAL_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "Error: Critical file missing after copy: $file"
        exit 1
    fi
done

# Set executable permissions
chmod +x ${RADIO_HOME}/manage_radio.sh
if [ -f "${RADIO_HOME}/install/reset_radio.sh" ]; then
    chmod +x ${RADIO_HOME}/install/reset_radio.sh
fi

echo "7. Setting up Python virtual environment..."
REQUIREMENTS_FILE="${RADIO_HOME}/install/requirements.txt"

# Verify requirements file exists
if [ ! -f "$REQUIREMENTS_FILE" ]; then
    echo "Error: requirements.txt not found at $REQUIREMENTS_FILE"
    exit 1
fi

sudo -u ${RADIO_USER} bash << EOF
python3 -m venv ${VENV_PATH}
source ${VENV_PATH}/bin/activate
pip install --upgrade pip
pip install -r "$REQUIREMENTS_FILE"
EOF

echo "8. Setting up audio and MPV..."
# Configure audio permissions
usermod -a -G audio ${RADIO_USER}
mkdir -p /run/user/1000/pulse
chown -R ${RADIO_USER}:${RADIO_USER} /run/user/1000/pulse

# Set up MPV socket directory
MPV_SOCKET_DIR="/tmp/mpv-socket"
mkdir -p "$MPV_SOCKET_DIR"
chown -R ${RADIO_USER}:${RADIO_USER} "$MPV_SOCKET_DIR"
chmod 755 "$MPV_SOCKET_DIR"

echo "9. Setting up wireless regulatory domain..."
# Get country code from Python config with proper PYTHONPATH
sudo -u ${RADIO_USER} bash << 'EOF'  # Note the quotes to prevent expansion
source ${VENV_PATH}/bin/activate
export PYTHONPATH=${RADIO_HOME}
python3 - << 'PYEOF'
try:
    from config.config import settings
    print(settings.COUNTRY_CODE)
except Exception as e:
    print("GB")  # Default to GB if config fails
PYEOF
EOF

COUNTRY_CODE=$(sudo -u ${RADIO_USER} bash -c "source ${VENV_PATH}/bin/activate && \
    PYTHONPATH=${RADIO_HOME} python3 -c 'from config.config import settings; print(settings.COUNTRY_CODE)' 2>/dev/null || echo 'GB'")

# Configure wireless regulatory domain
sudo tee /etc/default/crda <<EOF
REGDOMAIN=${COUNTRY_CODE}
EOF

# Configure wpa_supplicant country
sudo tee /etc/wpa_supplicant/wpa_supplicant.conf <<EOF
country=${COUNTRY_CODE}
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
EOF

# Configure hostapd country
sudo tee /etc/hostapd/hostapd.conf <<EOF
country_code=${COUNTRY_CODE}
EOF

echo "10. Setting up systemd service..."
# Create and configure radio service
sudo tee /etc/systemd/system/radio.service << EOF
[Unit]
Description=Internet Radio Service
After=network.target pigpiod.service avahi-daemon.service
Wants=network.target pigpiod.service avahi-daemon.service

[Service]
Type=simple
User=radio
Group=radio
WorkingDirectory=/home/radio/radio
Environment="PYTHONPATH=/home/radio/radio"
Environment="XDG_RUNTIME_DIR=/run/user/1000"
Environment="PULSE_RUNTIME_PATH=/run/user/1000/pulse"
# Python optimizations
Environment="PYTHONOPTIMIZE=2"
Environment="PYTHONDONTWRITEBYTECODE=1"
Environment="PYTHONUNBUFFERED=1"
RuntimeDirectory=radio
RuntimeDirectoryMode=0755

ExecStart=/home/radio/radio/manage_radio.sh start
ExecStop=/home/radio/radio/manage_radio.sh stop
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo chmod 644 /etc/systemd/system/radio.service
sudo systemctl daemon-reload
sudo systemctl enable radio.service

echo "11. Setting up permissions..."
chmod +x ${RADIO_HOME}/manage_radio.sh

echo "12. Starting radio service..."
${RADIO_HOME}/manage_radio.sh start

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