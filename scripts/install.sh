#!/bin/bash

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (use sudo)"
    exit 1
fi

echo "Starting installation..."

# Update package list
apt-get update

# Install required system packages
echo "Installing system dependencies..."
apt-get install -y \
    python3 \
    python3-pip \
    vlc \
    alsa-utils \
    git \
    libasound2-dev \
    python3-vlc \
    python3-tomli \
    python3-tomli-w \
    network-manager

# Install Python dependencies from requirements.txt
echo "Installing Python packages..."
pip3 install -r requirements.txt

# Create radio user if it doesn't exist
if ! id "radio" &>/dev/null; then
    useradd -m -s /bin/bash radio
fi

# Add radio user to required groups
usermod -a -G audio,video,gpio,netdev radio

# Create required directories
echo "Setting up directories..."
mkdir -p /home/radio/internetRadio/logs
mkdir -p /home/radio/internetRadio/config
mkdir -p /home/radio/internetRadio/sounds

# Set up sound configuration
echo 'pcm.!default {
    type hw
    card 0
}

ctl.!default {
    type hw
    card 0
}' > /etc/asound.conf

# Set up log rotation
cat << EOF > /etc/logrotate.d/radio
/home/radio/internetRadio/logs/radio.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    not
}
EOF

# Stop the service if it's running
systemctl stop radio 2>/dev/null || true

# Copy service file
cp systemd/radio.service /etc/systemd/system/

# Create initial config files if they don't exist
if [ ! -f "/home/radio/internetRadio/config/radio_state.json" ]; then
    echo '{"selected_stations": [], "current_stream": null}' > /home/radio/internetRadio/config/radio_state.json
    chown radio:radio /home/radio/internetRadio/config/radio_state.json
fi

# Set proper permissions for log directory
chown -R radio:radio /home/radio/internetRadio/logs
chmod 755 /home/radio/internetRadio/logs

# Reload systemd daemon
systemctl daemon-reload

# Enable and start the service
systemctl enable radio
systemctl start radio

# Create and configure radio.service
echo "Setting up systemd service..."
cat << EOF > /etc/systemd/system/radio.service
[Unit]
Description=Internet Radio Web Application
After=network-online.target sound.target
Wants=network-online.target sound.target

[Service]
Type=simple
User=radio
Group=audio
WorkingDirectory=/home/radio/internetRadio
Environment=PYTHONUNBUFFERED=1
Environment=FLASK_APP=app.py
Environment=FLASK_DEBUG=0
Environment=ALSA_CARD=0
Environment=ALSA_PCM_CARD=2
Environment=ALSA_DEVICE=hw:2,0
Environment=PULSE_SERVER=/run/pulse/native
Environment=PULSE_COOKIE=/run/pulse/cookie
Environment=PYTHONPATH=/home/radio/internetRadio
Environment=LD_LIBRARY_PATH=/usr/lib
ExecStart=/usr/bin/python3 /home/radio/internetRadio/main.py
ExecStop=/bin/kill -SIGTERM \$MAINPID
KillMode=control-group
TimeoutStopSec=10
Restart=on-failure
RestartSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Set correct permissions for service file
chmod 644 /etc/systemd/system/radio.service

# Set correct permissions for main.py
chmod +x /home/radio/internetRadio/main.py

# Add sudoers configuration for nmcli
echo "radio ALL=(ALL) NOPASSWD: /usr/bin/nmcli" > /etc/sudoers.d/radio-wifi
chmod 440 /etc/sudoers.d/radio-wifi

echo "Installation complete! Service is running."
echo "Check status with: systemctl status radio"
echo "View logs with: journalctl -u radio -f"