#!/bin/bash

# Exit on any error
set -e

# Simple locale fix
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

# Get script directory for absolute paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Create and activate virtual environment
echo "Setting up virtual environment..."
cd "$PROJECT_ROOT"
python3 -m venv venv
source venv/bin/activate

# Install pydantic in venv
pip install pydantic

# Get configuration from Python
get_config() {
    # Set default ports in case config fails
    export API_PORT=8000
    export DEV_PORT=3000
    export PROD_PORT=80
    export HOSTNAME=localhost

    # Try to get config from Python with correct path
    export PYTHONPATH="$PROJECT_ROOT"
    CONFIG_OUTPUT=$(python3 -c "
from config.config import settings
print(f'export API_PORT={settings.API_PORT}')
print(f'export DEV_PORT={settings.DEV_PORT}')
print(f'export PROD_PORT={settings.PROD_PORT}')
print(f'export HOSTNAME={settings.HOSTNAME}')
" 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo "$CONFIG_OUTPUT"
    else
        echo "export API_PORT=8000"
        echo "export DEV_PORT=3000"
        echo "export PROD_PORT=80"
        echo "export HOSTNAME=localhost"
        echo "# Warning: Using default port values" >&2
    fi
}

# Load configuration
eval "$(get_config)"

# Verify ports are set
echo "Using ports: API=$API_PORT, DEV=$DEV_PORT, PROD=$PROD_PORT"

echo "Installing development dependencies..."

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

# Install Python dependencies in venv
echo "Installing Python dependencies..."
pip install -r "${SCRIPT_DIR}/requirements.txt"
pip install -r "${SCRIPT_DIR}/requirements-dev.txt"

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
