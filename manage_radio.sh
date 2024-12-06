#!/bin/bash

APP_NAME="radio"
VENV_PATH="/home/radio/radio/venv"
APP_PATH="/home/radio/radio/src/api/main.py"
LOG_FILE="/home/radio/radio/logs/radio.log"
PID_FILE="/tmp/${APP_NAME}.pid"
API_PORT=80
DEV_PORT=5173

check_ports() {
    # Check and kill any existing processes on API_PORT
    if sudo lsof -Pi :$API_PORT -sTCP:LISTEN -t >/dev/null ; then
        echo "Port $API_PORT is already in use. Stopping existing process..."
        sudo kill -9 $(sudo lsof -t -i:$API_PORT)
        sleep 2
    fi
    
    # Check and kill any existing processes on DEV_PORT
    if lsof -Pi :$DEV_PORT -sTCP:LISTEN -t >/dev/null ; then
        echo "Port $DEV_PORT is already in use. Stopping existing process..."
        sudo kill -9 $(lsof -t -i:$DEV_PORT)
        sleep 2
    fi

    # Additional check for any hanging processes
    sudo pkill -f "uvicorn.*$APP_PATH" || true
    pkill -f "npm run dev" || true
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
EOF
        sudo chmod 440 $SUDO_FILE
    fi
}

start() {
    echo "Starting $APP_NAME..."
    check_ports
    check_pigpiod
    check_nmcli_permissions
    source $VENV_PATH/bin/activate
    echo "Virtual environment activated"
    
    # Clear the log file
    echo "" > $LOG_FILE
    
    # Start FastAPI server with sudo and preserve environment
    echo "Starting FastAPI server on port $API_PORT..."
    sudo -E env "PATH=$PATH" "$VENV_PATH/bin/uvicorn" src.api.main:app \
        --host 0.0.0.0 \
        --port $API_PORT \
        --reload \
        --log-level debug > $LOG_FILE 2>&1 &
    API_PID=$!
    echo $API_PID > $PID_FILE
    
    # Wait to ensure API server is up
    sleep 5
    
    # Verify API server is running
    if ! curl -s http://localhost:$API_PORT/api/v1/health > /dev/null; then
        echo "Failed to start API server. Check logs:"
        tail -n 20 $LOG_FILE
        exit 1
    fi
    
    # Start development server
    echo "Starting development server on port $DEV_PORT..."
    cd web && npm run dev -- --host 0.0.0.0 --port $DEV_PORT >> $LOG_FILE 2>&1 &
    DEV_PID=$!
    echo $DEV_PID >> $PID_FILE
    
    # Wait to ensure both servers start
    sleep 3
    
    # Check if processes are running
    if ps -p $API_PID > /dev/null && ps -p $DEV_PID > /dev/null; then
        echo "$APP_NAME started successfully"
        echo "FastAPI PID: $API_PID"
        echo "Dev Server PID: $DEV_PID"
        echo "Initial log entries:"
        tail -n 10 $LOG_FILE
    else
        echo "Failed to start $APP_NAME. Check logs for details."
        cat $LOG_FILE
        rm -f $PID_FILE
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
        rm -f $PID_FILE
        echo "$APP_NAME stopped."
        
        # Kill any remaining processes
        sudo pkill -f "uvicorn.*$APP_PATH"
        pkill -f "npm run dev"
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