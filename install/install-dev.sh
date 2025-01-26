#!/bin/bash

# Exit on any error
set -e

# Simple locale fix
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

echo "Installing development dependencies for Internet Radio project..."

# Update package list
echo "Updating package list..."
sudo apt-get update

# Install system dependencies
echo "Installing system dependencies..."
sudo apt-get install -y \
    git \
    curl \
    python3 \
    python3-pip \
    python3-venv \
    build-essential

# Install Docker
echo "Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
else
    echo "Docker already installed"
fi

# Install Docker Compose
echo "Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo apt-get install -y docker-compose
else
    echo "Docker Compose already installed"
fi

# Install Node.js and npm
echo "Installing Node.js and npm..."
if ! command -v node &> /dev/null; then
    # Install Node.js LTS using nvm
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    nvm install --lts
    nvm use --lts
else
    echo "Node.js already installed"
fi

# Ensure Docker service is properly configured and running
echo "Configuring Docker service..."
sudo systemctl enable docker
sudo systemctl start docker

# Add current user to docker group if not already in it
if ! groups | grep -q docker; then
    echo "Adding user to docker group..."
    sudo usermod -aG docker $USER
    echo "Updating group membership..."
    exec newgrp docker
fi

echo "Installation complete! You can now run ./dev.sh start to begin development."
