#!/bin/bash

APP_NAME="radio"
VENV_PATH="/home/radio/radio/venv"
APP_PATH="/home/radio/radio/src/api/main.py"
LOG_FILE="/home/radio/radio/logs/radio.log"
PID_FILE="/tmp/${APP_NAME}.pid"
API_PORT=80
DEV_PORT=5173

# Create PID file with proper permissions
setup_pid_file() {
    # Remove existing PID file if any
    sudo rm -f "$PID_FILE"
    
    # Create new PID file and set permissions
    sudo touch "$PID_FILE"
    sudo chown radio:radio "$PID_FILE"
    sudo chmod 644 "$PID_FILE"
}

check_ports() {
    # Function to kill process on a port
    kill_port() {
        local port=$1
        if sudo lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
            echo "Port $port is in use. Stopping process..."
            sudo kill -15 $(sudo lsof -t -i:$port) 2>/dev/null || true
            sleep 2
            sudo kill -9 $(sudo lsof -t -i:$port) 2>/dev/null || true
        fi
    }

    # Kill any existing uvicorn processes
    if pgrep -f "uvicorn.*$APP_PATH" >/dev/null; then
        echo "Stopping existing uvicorn process..."
        sudo pkill -15 -f "uvicorn.*$APP_PATH"
        sleep 2
        sudo pkill -9 -f "uvicorn.*$APP_PATH"
    fi

    # Kill any existing npm processes
    if pgrep -f "npm run dev" >/dev/null; then
        echo "Stopping existing npm process..."
        sudo pkill -15 -f "npm run dev"
        sleep 2
        sudo pkill -9 -f "npm run dev"
    fi

    # Check specific ports
    kill_port $API_PORT
    kill_port $DEV_PORT

    # Final verification
    sleep 2
    if sudo lsof -Pi :$API_PORT -sTCP:LISTEN -t >/dev/null || \
       sudo lsof -Pi :$DEV_PORT -sTCP:LISTEN -t >/dev/null; then
        echo "Failed to free ports. Please check manually."
        exit 1
    fi
}

check_pigpiod() {
    if ! pgrep -x "pigpiod" > /dev/null; then
        echo "Starting pigpiod..."
        sudo systemctl start pigpiod
    else
        echo "pigpiod is already running."
    fi
}

check_nmcli_permissions() {
    # Create sudo rule for nmcli if it doesn't exist
    SUDO_FILE="/etc/sudoers.d/radio-nmcli"
    if [ ! -f "$SUDO_FILE" ]; then
        echo "Setting up nmcli permissions..."
        sudo tee $SUDO_FILE <<EOF
# Allow radio user to run specific nmcli commands without password
radio ALL=(ALL) NOPASSWD: /usr/bin/nmcli device wifi list
radio ALL=(ALL) NOPASSWD: /usr/bin/nmcli device wifi rescan
radio ALL=(ALL) NOPASSWD: /usr/bin/nmcli networking connectivity check
radio ALL=(ALL) NOPASSWD: /usr/bin/nmcli device wifi connect *
radio ALL=(ALL) NOPASSWD: /usr/bin/nmcli connection up *
radio ALL=(ALL) NOPASSWD: /usr/bin/nmcli connection delete *
radio ALL=(ALL) NOPASSWD: /usr/bin/nmcli connection show
EOF
        sudo chmod 440 $SUDO_FILE
    fi
}

open_monitor() {
    echo "Opening monitor website..."
    # Wait for services to be fully up
    sleep 5
    
    # Check if Chromium is already running with monitor page
    if ! pgrep -f "chromium.*monitor" > /dev/null; then
        # Kill any existing Chromium instances first
        pkill chromium 2>/dev/null || true
        sleep 1
        
        # Open Chromium with proper flags
        DISPLAY=:0 chromium-browser \
            --kiosk \
            --start-fullscreen \
            --disable-restore-session-state \
            --noerrdialogs \
            --disable-session-crashed-bubble \
            --no-first-run \
            "http://localhost:5173/monitor" > /dev/null 2>&1 &
    else
        echo "Monitor already open in browser"
    fi
}

verify_process() {
    local pid=$1
    local name=$2
    local max_attempts=30
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if ! ps -p $pid > /dev/null; then
            echo "Process $name failed to start"
            return 1
        fi
        attempt=$((attempt + 1))
        sleep 1
    done
    return 0
}

start() {
    echo "Starting $APP_NAME..."
    check_ports
    check_pigpiod
    check_nmcli_permissions
    
    # Setup PID file with proper permissions first
    setup_pid_file
    
    source $VENV_PATH/bin/activate
    echo "Virtual environment activated"
    
    # Start FastAPI server with nohup
    echo "Starting FastAPI server on port $API_PORT..."
    nohup sudo -E env "PATH=$PATH" "$VENV_PATH/bin/uvicorn" src.api.main:app \
        --host 0.0.0.0 \
        --port $API_PORT \
        --reload \
        --log-level debug > $LOG_FILE 2>&1 &
    API_PID=$!
    sudo -u radio bash -c "echo $API_PID > $PID_FILE"
    
    # Wait for FastAPI to be ready
    echo "Waiting for FastAPI server to be ready..."
    max_attempts=30
    attempt=0
    while [ $attempt -lt $max_attempts ]; do
        if curl -s http://localhost:$API_PORT/api/v1/health > /dev/null; then
            echo "FastAPI server is ready"
            break
        fi
        attempt=$((attempt + 1))
        sleep 1
        echo "Waiting... ($attempt/$max_attempts)"
    done
    
    if [ $attempt -eq $max_attempts ]; then
        echo "Failed to start FastAPI server. Check logs:"
        tail -n 50 $LOG_FILE
        exit 1
    fi
    
    # Start development server with nohup and proper environment
    echo "Starting development server on port $DEV_PORT..."
    cd web
    # Clear any existing node processes
    sudo pkill -f "node.*vite" || true
    
    # Export environment variables
    export VITE_API_BASE="http://localhost:$API_PORT"
    export NODE_ENV="development"
    
    # Start dev server with full output
    nohup npm run dev -- \
        --host 0.0.0.0 \
        --port $DEV_PORT \
        --clearScreen false \
        >> $LOG_FILE 2>&1 &
    DEV_PID=$!
    sudo -u radio bash -c "echo $DEV_PID >> $PID_FILE"
    
    # Return to original directory
    cd ..
    
    # Wait for dev server with better checking
    echo "Waiting for development server to be ready..."
    attempt=0
    while [ $attempt -lt $max_attempts ]; do
        # Check if process is still running
        if ! ps -p $DEV_PID > /dev/null; then
            echo "Development server process died. Check logs:"
            tail -n 50 $LOG_FILE
            exit 1
        fi
        
        # Try to connect to dev server
        if curl -s http://localhost:$DEV_PORT > /dev/null; then
            echo "Development server is ready"
            break
        fi
        
        # Show recent logs if taking too long
        if [ $attempt -eq 15 ]; then
            echo "Recent development server logs:"
            tail -n 20 $LOG_FILE
        fi
        
        attempt=$((attempt + 1))
        sleep 1
        echo "Waiting... ($attempt/$max_attempts)"
    done
    
    if [ $attempt -eq $max_attempts ]; then
        echo "Failed to start development server. Check logs:"
        tail -n 50 $LOG_FILE
        exit 1
    fi
    
    # Final verification
    if ps -p $API_PID > /dev/null && ps -p $DEV_PID > /dev/null; then
        echo "$APP_NAME started successfully"
        echo "FastAPI PID: $API_PID"
        echo "Dev Server PID: $DEV_PID"
        echo "Initial log entries:"
        tail -n 10 $LOG_FILE
        
        # Open monitor website
        open_monitor
    else
        echo "Failed to start $APP_NAME. Check logs for details."
        cat $LOG_FILE
        sudo rm -f $PID_FILE
        exit 1
    fi
}

stop() {
    if [ -f $PID_FILE ]; then
        while read PID; do
            echo "Stopping process with PID $PID..."
            sudo kill -15 $PID 2>/dev/null || true
            sleep 2
            # Force kill if still running
            sudo kill -9 $PID 2>/dev/null || true
        done < $PID_FILE
        sudo rm -f $PID_FILE
        echo "$APP_NAME stopped."
        
        # Kill any remaining processes
        sudo pkill -f "uvicorn.*$APP_PATH" || true
        sudo pkill -f "npm run dev" || true
    else
        echo "$APP_NAME is not running."
    fi
    
    # Double check ports are free
    check_ports
}

restart() {
    echo "Restarting $APP_NAME..."
    stop
    sleep 2
    start
}

status() {
    if [ -f $PID_FILE ]; then
        PID=$(cat $PID_FILE)
        if ps -p $PID > /dev/null; then
            echo "$APP_NAME is running with PID $PID"
            echo "Recent logs:"
            tail -n 5 $LOG_FILE
        else
            echo "$APP_NAME is not running (stale PID file found)"
            rm -f $PID_FILE
        fi
    else
        echo "$APP_NAME is not running"
    fi
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
esac