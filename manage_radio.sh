#!/bin/bash

APP_NAME="radio"
VENV_PATH="/home/radio/radio/venv"
APP_PATH="/home/radio/radio/src/api/main.py"
LOG_FILE="/home/radio/radio/logs/radio.log"
PID_FILE="/tmp/${APP_NAME}.pid"
PORT=8000

check_port() {
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null ; then
        echo "Port $PORT is already in use. Stopping existing process..."
        sudo kill -9 $(sudo lsof -t -i:$PORT)
        sleep 2
    fi
}

start() {
    echo "Starting $APP_NAME..."
    check_port
    source $VENV_PATH/bin/activate
    echo "Virtual environment activated"
    
    # Clear the log file
    echo "" > $LOG_FILE
    
    nohup uvicorn src.api.main:app --host 0.0.0.0 --port $PORT --reload > $LOG_FILE 2>&1 &
    PID=$!
    echo $PID > $PID_FILE
    
    # Wait a moment to ensure the application starts
    sleep 2
    
    # Check if the process is still running
    if ps -p $PID > /dev/null; then
        echo "$APP_NAME started successfully with PID $PID"
    else
        echo "Failed to start $APP_NAME. Check logs for details."
        cat $LOG_FILE
        rm -f $PID_FILE
    fi
}

stop() {
    if [ -f $PID_FILE ]; then
        PID=$(cat $PID_FILE)
        echo "Stopping $APP_NAME with PID $PID..."
        kill -15 $PID 2>/dev/null || true
        sleep 2
        # Force kill if still running
        kill -9 $PID 2>/dev/null || true
        rm -f $PID_FILE
        echo "$APP_NAME stopped."
        
        # Kill any remaining uvicorn processes
        pkill -f "uvicorn.*$APP_PATH"
    else
        echo "$APP_NAME is not running."
    fi
    
    # Double check port is free
    check_port
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