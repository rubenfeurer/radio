#!/bin/bash

# Get script directory for absolute paths
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate virtual environment
source "${SCRIPT_DIR}/venv/bin/activate"

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

# Check for running instances
check_running() {
    if [ -f "/tmp/radio.pid" ]; then
        echo "Radio service is already running. Stop it first:"
        echo "./manage_radio.sh stop"
        exit 1
    fi
}

# Check ports
check_ports() {
    echo "Checking ports: API=$API_PORT, DEV=$DEV_PORT..."
    for port in $API_PORT $DEV_PORT; do
        if lsof -i ":$port" >/dev/null 2>&1; then
            echo "Port $port is in use. Stopping processes..."
            sudo lsof -ti ":$port" | xargs sudo kill -9 2>/dev/null
        fi
    done
    sleep 2
}

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
    # Kill any process using port 3000
    fuser -k 3000/tcp 2>/dev/null || true
    # Kill npm run dev processes
    pkill -f "npm run dev" || true
    # Kill node processes related to vite
    pkill -f "vite" || true
    # Wait a moment for the ports to be released
    sleep 3
}

# Function to run tests in existing Docker container
run_tests() {
    echo "Running tests in Docker container..."
    docker compose -f docker/compose/docker-compose.dev.yml exec backend /home/radio/radio/venv/bin/python -m pytest "$@"
}

# Function to run tests in clean container
run_tests_clean() {
    echo "Running tests in clean Docker container..."
    docker compose -f docker/compose/docker-compose.dev.yml run --rm backend /home/radio/radio/venv/bin/python -m pytest "$@"
}

# Function to check and install pre-commit
check_precommit() {
    echo "Checking pre-commit installation..."

    # Disable git locale warnings
    git config --global advice.setLocale false

    # Clean up any stale git locks first
    cleanup_git_locks

    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi

    # Add venv/bin to PATH
    export PATH="$PWD/venv/bin:$PATH"

    # Activate virtual environment
    echo "Activating virtual environment..."
    source venv/bin/activate || source venv/Scripts/activate

    # Install pre-commit locally if not present
    if ! command -v pre-commit >/dev/null 2>&1; then
        echo "Installing pre-commit locally..."
        pip install pre-commit
    fi

    # Install required packages for config
    pip install pydantic

    # Unset core.hooksPath before installing hooks
    echo "Unsetting core.hooksPath..."
    git config --unset-all core.hooksPath

    # Install pre-commit hooks locally
    echo "Installing pre-commit hooks locally..."
    pre-commit install

    # Create a wrapper script for pre-commit in .git/hooks
    cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
source "$(dirname "$0")/../../venv/bin/activate"
exec pre-commit run --hook-stage pre-commit
EOF

    # Make the wrapper script executable
    chmod +x .git/hooks/pre-commit

    # Deactivate virtual environment
    deactivate

    echo "Pre-commit setup complete"
}

# Function to detect hardware environment
detect_environment() {
    if [ -f /etc/rpi-issue ] || [ -f /proc/device-tree/model ] && grep -q "Raspberry Pi" /proc/device-tree/model; then
        echo "Running on Raspberry Pi - using real hardware"
        export MOCK_SERVICES=false
    elif [ "$CI" = "true" ]; then
        echo "Running in CI environment - using mocks"
        export MOCK_SERVICES=true
    else
        echo "Running on development machine - using mocks"
        export MOCK_SERVICES=true
    fi
}

# Start development environment
start_dev() {
    check_running
    check_ports
    detect_environment

    echo "Starting development environment using Docker..."

    # Stop any existing containers and processes
    docker compose -f docker/compose/docker-compose.dev.yml down
    kill_frontend

    # Start Docker services
    docker compose -f docker/compose/docker-compose.dev.yml up -d --build

    # Wait for services to be ready
    echo "Waiting for services to start..."
    for i in {1..30}; do
        if curl -s "http://localhost:$API_PORT/api/v1/health" >/dev/null; then
            echo "Development environment started:"
            echo "Backend: http://localhost:$API_PORT"
            echo "Frontend: http://localhost:$DEV_PORT"
            echo "Use './dev.sh stop' to stop the development environment"
            return 0
        fi
        sleep 1
    done

    echo "Error: Services failed to start"
    docker compose -f docker/compose/docker-compose.dev.yml logs
    return 1
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

# Add this new function
cleanup_git_locks() {
    echo "Cleaning up git lock files..."
    rm -f .git/index.lock
    rm -f .git/refs/heads/*.lock
    rm -f .git/*.lock
    git gc --prune=now
}

# Add this new function
update_deps() {
    echo "Updating dependencies..."

    # Update pre-commit hooks
    pre-commit clean
    pre-commit autoupdate

    # Update frontend dependencies if web directory exists
    if [ -d "web" ]; then
        echo "Updating frontend dependencies..."
        cd web
        npm update
        cd ..
    fi

    # Rebuild Docker containers with fresh dependencies
    echo "Rebuilding Docker containers with updated dependencies..."
    docker compose -f docker/compose/docker-compose.dev.yml down
    docker compose -f docker/compose/docker-compose.dev.yml build --no-cache
    docker compose -f docker/compose/docker-compose.dev.yml up -d

    echo "Dependencies updated successfully"
}

# Main script
check_docker
check_node

case "$1" in
    "start")
        start_dev
        ;;
    "stop")
        docker compose -f docker/compose/docker-compose.dev.yml down
        kill_frontend
        ;;
    "logs")
        docker compose -f docker/compose/docker-compose.dev.yml logs -f
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
    "setup-hooks")
        check_precommit
        ;;
    "cleanup")
        cleanup_git_locks
        ;;
    "update")
        update_deps
        ;;
    *)
        echo "Usage: $0 {start|stop|logs|rebuild|test|test-clean|lint|test-all|fix|setup-hooks|cleanup|update}"
        exit 1
        ;;
esac
