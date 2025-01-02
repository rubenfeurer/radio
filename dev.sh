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

# Function to run tests in existing Docker container
run_tests() {
    echo "Running tests in Docker container..."
    docker compose -f docker/docker-compose.dev.yml exec backend /home/radio/radio/venv/bin/python -m pytest "$@"
}

# Function to run tests in clean container
run_tests_clean() {
    echo "Running tests in clean Docker container..."
    docker compose -f docker/docker-compose.dev.yml run --rm backend /home/radio/radio/venv/bin/python -m pytest "$@"
}

# Function to check and install pre-commit
check_precommit() {
    echo "Checking pre-commit installation..."
    
    # Check if pre-commit is installed in the backend container
    if ! docker compose -f docker/docker-compose.dev.yml exec backend bash -c "source /home/radio/radio/venv/bin/activate && pre-commit --version" >/dev/null 2>&1; then
        echo "Installing pre-commit in backend container..."
        docker compose -f docker/docker-compose.dev.yml exec backend bash -c "
            source /home/radio/radio/venv/bin/activate && \
            pip install pre-commit && \
            pre-commit install
        "
    else
        echo "pre-commit is already installed"
    fi

    # Check if hooks are installed
    if ! docker compose -f docker/docker-compose.dev.yml exec backend bash -c "[ -f .git/hooks/pre-commit ]"; then
        echo "Installing pre-commit hooks..."
        docker compose -f docker/docker-compose.dev.yml exec backend bash -c "
            source /home/radio/radio/venv/bin/activate && \
            pre-commit install
        "
    fi
}

# Function to start development environment
start_dev() {
    echo "Starting development environment..."
    
    # Kill any existing frontend process
    kill_frontend
    
    # Start backend container
    docker compose -f docker/docker-compose.dev.yml up -d --build

    # Install pre-commit if needed
    check_precommit

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

# Function to run linting checks
run_lint() {
    echo "Running linting checks..."
    docker compose -f docker/docker-compose.dev.yml exec backend bash -c "
        source /home/radio/radio/venv/bin/activate && \
        black --check src tests && \
        ruff check \
            --ignore E501,D100,D101,D102,D103,D104,D105,D106,D107,D400,D415,ANN201,ANN202,ANN001,S101,SLF001,ARG001 \
            src tests && \
        mypy src --config-file mypy.ini && \
        pylint --disable=C0111,C0114,C0115,C0116,E1101,R0801,R0903,W0511,C0103 src tests
    "
}

# Function to run all checks (tests + lint)
run_all_checks() {
    echo "Running all checks (lint + tests)..."
    run_lint
    if [ $? -eq 0 ]; then
        run_tests "$@"
    else
        echo "Linting failed! Please fix linting issues before running tests."
        exit 1
    fi
}

# Function to auto-fix code issues
run_fix() {
    echo "Auto-fixing code issues..."
    
    # Check if backend is running
    if ! docker compose -f docker/docker-compose.dev.yml ps --status running backend >/dev/null 2>&1; then
        echo "Starting backend container..."
        docker compose -f docker/docker-compose.dev.yml up -d --build backend
        sleep 5
    fi

    # Run the fix commands
    if docker compose -f docker/docker-compose.dev.yml ps --status running backend >/dev/null 2>&1; then
        docker compose -f docker/docker-compose.dev.yml exec backend bash -c "
            source /home/radio/radio/venv/bin/activate && \
            # Format with Black (force write)
            black --fast --force-exclude '/\.' src tests && \
            # Fix imports
            isort --atomic src tests && \
            # Run ruff with all fixes enabled
            ruff check --fix --unsafe-fixes --ignore E501,D100,D101,D102,D103,D104,D105,D106,D107,D400,D415,ANN201,ANN202,ANN001,S101,SLF001,ARG001 src tests && \
            # Final Black pass to ensure consistency
            black --fast --force-exclude '/\.' src tests
        "
    else
        echo "Error: Backend service failed to start"
        exit 1
    fi
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
    "test")
        shift  # Remove 'test' from arguments
        run_tests "$@"
        ;;
    "test-clean")
        shift  # Remove 'test-clean' from arguments
        run_tests_clean "$@"
        ;;
    "lint")
        run_lint
        ;;
    "test-all")
        run_all_checks "${@:2}"
        ;;
    "fix")
        run_fix
        ;;
    *)
        echo "Usage: $0 {start|stop|logs|rebuild|test|test-clean|lint|test-all|fix}"
        exit 1
        ;;
esac 