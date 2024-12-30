#!/bin/bash

# Function to check Docker status
check_docker() {
    if ! docker info >/dev/null 2>&1; then
        echo "Docker is not running. Please start Docker first."
        exit 1
    fi
}

# Function to check Node.js and npm
check_node() {
    if ! command -v npm &> /dev/null; then
        echo "npm not found. Please install Node.js and npm first."
        echo "Visit: https://nodejs.org/"
        exit 1
    fi
}

# Function to check and install frontend dependencies
check_frontend_deps() {
    if [ -d "web" ]; then
        if [ ! -d "web/node_modules" ]; then
            echo "Installing frontend dependencies..."
            cd web
            npm install
            cd ..
        fi
    fi
}

# Function to kill existing frontend process
kill_frontend() {
    echo "Stopping any running frontend processes..."
    pkill -f "npm run dev" || true
    # Wait a moment for the port to be released
    sleep 2
}

# Function to start development environment
start_dev() {
    echo "Starting development environment..."
    
    # Kill any existing frontend process
    kill_frontend
    
    # Start backend container
    docker compose -f docker/docker-compose.dev.yml up -d --build

    # Check and start frontend
    if [ -d "web" ]; then
        check_frontend_deps
        echo "Starting frontend development server..."
        cd web
        npm run dev &
        cd ..
    else
        echo "No frontend directory found. Skipping frontend startup."
    fi

    # Wait for all background processes
    wait
}

# Function to rebuild environment
rebuild_dev() {
    echo "Rebuilding development environment..."
    
    # Kill any existing frontend process
    kill_frontend
    
    # Rebuild backend
    docker compose -f docker/docker-compose.dev.yml down
    docker compose -f docker/docker-compose.dev.yml rm -f
    docker rmi radio-backend
    docker compose -f docker/docker-compose.dev.yml up -d --build
    
    # Check and start frontend
    if [ -d "web" ]; then
        check_frontend_deps
        echo "Starting frontend development server..."
        cd web
        npm run dev &
        cd ..
    fi

    # Wait for all background processes
    wait
}

# Main script
check_docker
check_node

case "$1" in
    "start")
        start_dev
        ;;
    "stop")
        docker compose -f docker/docker-compose.dev.yml down
        kill_frontend
        ;;
    "logs")
        docker compose -f docker/docker-compose.dev.yml logs -f
        ;;
    "rebuild")
        rebuild_dev
        ;;
    *)
        echo "Usage: $0 {start|stop|logs|rebuild}"
        exit 1
        ;;
esac 