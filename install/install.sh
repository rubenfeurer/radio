#!/bin/bash

# Exit on error
set -e

echo "Starting Internet Radio installation..."

# Configuration
RADIO_USER="radio"
RADIO_HOME="/home/${RADIO_USER}/radio"
VENV_PATH="${RADIO_HOME}/venv"
SKIP_PIGPIO=${SKIP_PIGPIO:-0}

# Docker environment check
DOCKER_ENV=0
if [ -f /.dockerenv ] || [ "$TEST_MODE" = "1" ]; then
    DOCKER_ENV=1
fi

# Define installation functions first
install_system_dependencies() {
    echo "Installing system dependencies..."
    while read -r line; do
        # Skip comments and empty lines
        [[ $line =~ ^#.*$ ]] && continue
        [[ -z $line ]] && continue

        # Handle pigpio specially
        if [ "$line" = "pigpio" ]; then
            if [ "$SKIP_PIGPIO" = "1" ]; then
                echo "Skipping pigpio installation (SKIP_PIGPIO=1)"
                continue
            fi
            # Check if already installed from source
            if command -v pigpiod >/dev/null 2>&1; then
                echo "pigpio already installed, skipping..."
                continue
            fi
            echo "pigpio package not available, skipping apt install..."
            continue
        fi

        echo "Installing $line..."
        apt-get install -y $line || {
            echo "Warning: Failed to install $line"
            if [ "$line" != "pigpio" ]; then
                exit 1
            fi
        }
    done < install/system-requirements.txt
}

if [ "$DOCKER_ENV" = "1" ]; then
    echo "Docker environment detected - running minimal installation"

    # Create radio user if doesn't exist
    id -u ${RADIO_USER} &>/dev/null || useradd -m ${RADIO_USER}

    # Add to audio group
    usermod -a -G audio ${RADIO_USER}

    # Install dependencies and set up environment
    install_system_dependencies

    # Rest of Docker installation...
    exit 0
fi

# Create minimal environment
echo "Setting up minimal Docker environment..."

# Create radio user and home directory
useradd -m ${RADIO_USER}
mkdir -p ${RADIO_HOME}
chown -R ${RADIO_USER}:${RADIO_USER} ${RADIO_HOME}

# Install only essential system packages
apt-get update
while read -r line; do
    [[ $line =~ ^#.*$ ]] && continue
    [[ -z $line ]] && continue
    # Skip hardware-specific packages in Docker
    [[ $line == "pigpio" ]] && continue
    [[ $line == "alsa-utils" ]] && continue
    [[ $line == "network-manager" ]] && continue
    apt-get install -y $line
done < install/system-requirements.txt
rm -rf /var/lib/apt/lists/*

# Install core Python dependencies only
python3 -m venv ${VENV_PATH}
source ${VENV_PATH}/bin/activate
pip install --no-cache-dir -r install/requirements.txt

exit 0

SKIP_PIGPIO=${SKIP_PIGPIO:-0}
TEST_MODE=${TEST_MODE:-0}

echo "1. Installing system dependencies..."
apt-get update

# Install system dependencies from file
while read -r line; do
    # Skip comments and empty lines
    [[ $line =~ ^#.*$ ]] && continue
    [[ -z $line ]] && continue

    echo "Installing $line..."
    if [ "$line" = "pigpio" ]; then
        if [ "$SKIP_PIGPIO" = "1" ]; then
            echo "Skipping pigpio installation (SKIP_PIGPIO=1)"
            continue
        fi
        # Try to install pigpio but don't fail if not available
        apt-get install -y pigpio || {
            echo "Warning: pigpio installation skipped (not available)"
            continue
        }
    else
        # Install other packages normally
        apt-get install -y $line || exit 1
    fi
done < install/system-requirements.txt

# Skip pigpio service setup if flag is set or installation failed
if [ "$SKIP_PIGPIO" != "1" ] && command -v pigpiod >/dev/null 2>&1; then
    echo "2. Setting up pigpiod service..."
    systemctl enable pigpiod || true
    systemctl start pigpiod || true
fi

echo "3. Creating radio user..."
# Create radio user if not exists
if ! id "${RADIO_USER}" &>/dev/null; then
    useradd -m ${RADIO_USER}

    # Add to groups based on environment
    if [ "$TEST_MODE" = "1" ] || [ "$SKIP_PIGPIO" = "1" ]; then
        # Minimal groups for test environment
        usermod -a -G audio,dialout,pulse-access,netdev ${RADIO_USER}
    else
        # All groups for production environment
        # Create gpio group if it doesn't exist
        getent group gpio || groupadd gpio
        usermod -a -G audio,gpio,dialout,pulse-access,netdev ${RADIO_USER}
    fi
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

# Network Service Management
echo "Configuring network services..."

if [ "$DOCKER_ENV" = "1" ]; then
    echo "Docker/Test environment detected - skipping network service management"
else
    # Stop and disable all potentially conflicting network services
    NETWORK_SERVICES=(
        "dhcpcd"
        "wpa_supplicant"
        "systemd-networkd"
        "raspberrypi-net-mods"
    )

    for service in "${NETWORK_SERVICES[@]}"; do
        echo "Disabling $service..."
        if systemctl is-active --quiet $service; then
            systemctl stop $service
            systemctl disable $service
            systemctl mask $service
        else
            echo "$service is already disabled"
        fi
    done

    # Ensure NetworkManager is enabled and running
    echo "Enabling NetworkManager..."
    systemctl enable NetworkManager
    systemctl restart NetworkManager
fi

# Ensure consistent network interface naming
echo "Configuring network interface naming..."
sudo tee /etc/udev/rules.d/72-wlan-geo-dependent.rules <<EOF
ACTION=="add", SUBSYSTEM=="net", DRIVERS=="brcmfmac", NAME="wlan0"
EOF

# Configure NetworkManager
sudo tee /etc/NetworkManager/NetworkManager.conf <<EOF
[main]
plugins=ifupdown,keyfile
dhcp=internal
dns=default
no-auto-default=*

[ifupdown]
managed=true

[device]
wifi.scan-rand-mac-address=no

[connection]
wifi.mac-address-randomization=1
EOF

# Wait for NetworkManager to be ready
sleep 2

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

echo "10. Setting up systemd service..."
# Create and configure radio service
sudo tee /etc/systemd/system/radio.service <<EOF
[Unit]
Description=Internet Radio Service
After=network.target pigpiod.service
Wants=network.target pigpiod.service

[Service]
Type=simple
User=radio
Group=radio
WorkingDirectory=/home/radio/radio
Environment="PYTHONPATH=/home/radio/radio"
Environment="XDG_RUNTIME_DIR=/run/user/1000"
Environment="PULSE_RUNTIME_PATH=/run/user/1000/pulse"
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

# Reload systemd to apply changes
systemctl daemon-reload

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

# Add NetworkManager permissions for radio user
echo "Configuring NetworkManager permissions..."
sudo tee /etc/polkit-1/localauthority/50-local.d/radio.pkla <<EOF
[radio-network-control]
Identity=unix-user:radio
Action=org.freedesktop.NetworkManager.*
ResultAny=yes
ResultInactive=yes
ResultActive=yes
EOF

# Configure interface priorities
sudo tee /etc/NetworkManager/conf.d/10-interface-priority.conf <<EOF
[connection]
# Prefer wlan0 over other interfaces
match-device=interface-name:wlan0
ipv4.route-metric=50
ipv6.route-metric=50
EOF

# Configure NetworkManager DNS
sudo tee /etc/NetworkManager/conf.d/dns.conf <<EOF
[main]
dns=default
systemd-resolved=false

[global-dns-domain-*]
servers=1.1.1.1,8.8.8.8
EOF

# Add network recovery script with detailed logging
echo "Adding network recovery handler..."
sudo tee /etc/NetworkManager/dispatcher.d/99-radio-recovery <<EOF
#!/bin/bash

# Log function for better debugging
log_msg() {
    logger -t "radio-recovery" "\$1"
}

# Get interface name and status
IFACE="\$1"
STATUS="\$2"

log_msg "Network change detected: Interface=\$IFACE, Status=\$STATUS"

# Only handle wlan0 events
if [ "\$IFACE" != "wlan0" ]; then
    log_msg "Ignoring non-wlan0 interface"
    exit 0
fi

# Handle network state changes
if [ "\$STATUS" = "down" ] || [ "\$STATUS" = "up" ]; then
    log_msg "Checking radio service status..."

    # Check if service is active
    if ! systemctl is-active --quiet radio; then
        log_msg "Radio service is down, attempting restart..."
        systemctl restart radio

        # Verify restart
        if systemctl is-active --quiet radio; then
            log_msg "Radio service successfully restarted"
        else
            log_msg "Failed to restart radio service"
        fi
    else
        log_msg "Radio service is running normally"
    fi
fi
EOF

# Make the script executable
sudo chmod +x /etc/NetworkManager/dispatcher.d/99-radio-recovery

# Add pre-commit setup if in development mode
if [ "$DEV_MODE" = "true" ]; then
    echo "Setting up pre-commit hooks..."
    pre-commit install
fi

# Check if running in development environment
if [ -f docker-compose.dev.yml ]; then
    echo "Development environment detected"
    export DEV_MODE=true
else
    export DEV_MODE=false
fi

# Add pre-flight checks
echo "Running pre-flight checks..."
for cmd in nmcli ip systemctl logger; do
    if ! command -v $cmd >/dev/null 2>&1; then
        echo "Error: Required command '$cmd' not found"
        exit 1
    fi
done

# Verify wlan0 interface exists or wait for it
echo "Verifying network interface..."
if ! ip link show wlan0 >/dev/null 2>&1; then
    echo "Warning: wlan0 interface not found"
    echo "Waiting for interface..."
    # Wait up to 30 seconds for interface
    for i in {1..30}; do
        if ip link show wlan0 >/dev/null 2>&1; then
            echo "Interface wlan0 found"
            break
        fi
        if [ $i -eq 30 ]; then
            echo "Error: wlan0 interface not found after 30 seconds"
            exit 1
        fi
        sleep 1
    done
fi

# Add installation validation function
validate_installation() {
    echo "Validating installation..."

    # Check critical services only if not in Docker/Test
    if [ "$DOCKER_ENV" != "1" ]; then
        for service in "NetworkManager" "radio"; do
            if [ "$SKIP_PIGPIO" != "1" ] && [ "$service" = "pigpiod" ]; then
                continue
            fi
            if ! systemctl is-active --quiet $service; then
                echo "Error: $service is not running"
                return 1
            fi
        done
    fi

    # Check radio user and permissions
    if ! id "radio" >/dev/null 2>&1; then
        echo "Error: radio user not found"
        return 1
    fi

    # Verify critical directories
    for dir in "/home/radio/radio"; do
        if [ ! -d "$dir" ]; then
            echo "Error: Directory $dir not found"
            return 1
        fi
    done

    # Skip NetworkManager directory check in Docker/Test
    if [ "$DOCKER_ENV" != "1" ] && [ ! -d "/etc/NetworkManager/system-connections" ]; then
        echo "Error: Directory /etc/NetworkManager/system-connections not found"
        return 1
    fi

    echo "✓ Installation validation successful"
    return 0
}

# Run validation at the end of installation
if ! validate_installation; then
    echo "! Installation validation failed"
    exit 1
fi

# Call the function where appropriate
install_system_dependencies
