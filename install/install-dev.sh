#!/bin/bash

# Exit on any error
set -e

# Simple locale fix
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

# Get configuration from Python
get_config() {
    python3 -c "
from config.config import settings
print(f'export API_PORT={settings.API_PORT}')
print(f'export DEV_PORT={settings.DEV_PORT}')
print(f'export PROD_PORT={settings.PROD_PORT}')
print(f'export HOSTNAME={settings.HOSTNAME}')
"
}

# Load configuration
eval "$(get_config)"

echo "Installing development dependencies..."
echo "Using ports: API=$API_PORT, DEV=$DEV_PORT, PROD=$PROD_PORT"

# Update and install system dependencies
sudo apt-get update
sudo apt-get install -y \
    git curl python3 python3-pip python3-venv build-essential

# Install Docker if needed
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
fi

# Install Docker Compose
if ! command -v docker-compose &> /dev/null; then
    sudo apt-get install -y docker-compose
fi

# Install Node.js using nvm
if ! command -v node &> /dev/null; then
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    nvm install --lts
    nvm use --lts
fi

# Configure Docker service
sudo systemctl enable docker
sudo systemctl start docker

# Add user to docker group
if ! groups | grep -q docker; then
    sudo usermod -aG docker $USER
    exec newgrp docker
fi

echo "Installation complete! You can now run ./dev.sh start to begin development."
