# radio

## Virtual Environment Setup

To ensure all dependencies are installed in an isolated environment, follow these steps to create and manage a virtual environment:

### Creating a Virtual Environment

1. **Navigate to the project directory**:
   ```bash
   cd ~/radio
   ```

2. **Create the virtual environment**:
   ```bash
   python3 -m venv venv
   ```

### Activating the Virtual Environment

- **On Linux/Mac**:
  ```bash
  source venv/bin/activate
  ```

- **On Windows**:
  ```bash
  .\venv\Scripts\activate
  ```

### Deactivating the Virtual Environment

To deactivate the virtual environment, simply run:
```bash
deactivate
```

## Development Setup

### Installing Dependencies

After activating the virtual environment, install the required packages:
```bash
pip install -r requirements.txt
```

### Running the Development Server

1. **Start the FastAPI server**:
   ```bash
   uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Access the API**:
   - Main API: `http://<raspberry-pi-ip>:8000`
   - Health Check: `http://<raspberry-pi-ip>:8000/health`
   - API Documentation: `http://<raspberry-pi-ip>:8000/docs`

   Replace `<raspberry-pi-ip>` with your Raspberry Pi's IP address (find it using `hostname -I`)

## Project Structure

```
radio/
├── config/         # Configuration files
├── install/        # Installation scripts
├── src/           # Source code
│   ├── api/       # API endpoints
│   ├── core/      # Business logic
│   ├── hardware/  # Hardware interfaces
│   ├── system/    # System management
│   └── utils/     # Utility functions
├── tests/         # Test files
├── venv/          # Virtual environment
└── README.md      # This file
```

## Configuration

- **Hardware Pins**: Configurable in `config.py`
- **Volume Behavior**: Adjust sensitivity and default settings in `config.py`

## Development Notes

- The server runs in development mode with auto-reload enabled
- API documentation is automatically generated at `/docs`
- CORS is enabled for all origins in development mode

## Logging

The application uses rotating log files to track events and errors. Logs are stored in the `logs` directory.

### Log File Location
- Main log file: `logs/radio.log`
- Rotating backup files: `radio.log.1`, `radio.log.2`, etc.
- Maximum log file size: 10MB
- Maximum number of backup files: 5

### Viewing Logs

1. **View the entire log file**:
   ```bash
   cat logs/radio.log
   ```

2. **Follow log updates in real-time**:
   ```bash
   tail -f logs/radio.log
   ```

3. **View last 50 lines**:
   ```bash
   tail -n 50 logs/radio.log
   ```

4. **Search logs for specific terms**:
   ```bash
   grep "ERROR" logs/radio.log
   ```

### Log Levels
- INFO: Normal operation events
- WARNING: Unexpected but handled events
- ERROR: Error conditions that need attention
- DEBUG: Detailed information for debugging

## Radio Manager

The `RadioManager` class handles the core functionality of the radio, including station management, playback control, and hardware interactions.

### Basic Usage

```python
from src.core.radio_manager import RadioManager
from src.core.models import RadioStation

# Initialize the radio manager
radio = RadioManager()

# Add a radio station
station = RadioStation(
    name="Example Radio",
    url="http://example.com/stream",
    slot=1
)
radio.add_station(station)

# Play a station
await radio.play_station(1)

# Control volume
await radio.set_volume(75)  # Set volume to 75%

# Stop playback
await radio.stop_playback()
```

### Hardware Controls

The RadioManager automatically handles hardware interactions:

- **Buttons**: 
  - Button 1: Play station in slot 1
  - Button 2: Play station in slot 2
  - Button 3: Play station in slot 3

- **Rotary Encoder**:
  - Clockwise: Increase volume
  - Counter-clockwise: Decrease volume

### Methods

- `add_station(station: RadioStation)`: Add or update a station in a slot
- `remove_station(slot: int)`: Remove a station from a slot
- `get_station(slot: int)`: Get station information for a slot
- `play_station(slot: int)`: Start playing the station in the specified slot
- `stop_playback()`: Stop the current playback
- `set_volume(volume: int)`: Set the volume (0-100)
- `get_status()`: Get the current system status

### System Status

The system status includes:
- Current volume level
- Currently playing station
- Playback status (playing/stopped)

## GPIO Setup

### Hardware Control
The application uses `pigpio` for GPIO management, providing:
- Reliable hardware control with microsecond precision
- Better timing accuracy for rotary encoder
- Hardware-timed PWM
- Stable interrupt handling

### Installation

1. **Install pigpio System Package**:
   ```bash
   sudo apt-get update
   sudo apt-get install pigpio python3-pigpio
   ```

2. **Enable GPIO Daemon**:
   ```bash
   # Enable pigpiod to start on boot
   sudo systemctl enable pigpiod

   # Start pigpiod immediately
   sudo systemctl start pigpiod

   # Check status
   sudo systemctl status pigpiod
   ```

### Troubleshooting GPIO

If hardware controls aren't working:

1. **Check GPIO Service Status**:
   ```bash
   sudo systemctl status pigpiod
   ```

2. **Restart GPIO Service**:
   ```bash
   sudo systemctl restart pigpiod
   ```

3. **Verify pigpio Installation**:
   ```bash
   # Test Python pigpio module
   python3 -c "import pigpio; pi = pigpio.pi(); print('Connected' if pi.connected else 'Not connected')"
   ```

4. **Enable Debug Logging**:
   - Set log level to DEBUG in configuration
   - Monitor hardware events:
     ```bash
     tail -f logs/radio.log | grep "GPIO"
     ```

5. **Check Hardware Connections**:
   - Verify pin numbers in config.py match physical connections
   - Check for loose wires or connections
   - Ensure proper grounding

## Application Management

The `manage_radio.sh` script provides easy control over the radio application. This script handles starting, stopping, restarting, and checking the status of the application.

### Basic Usage

```bash
# Start the application
./manage_radio.sh start

# Stop the application
./manage_radio.sh stop

# Restart the application
./manage_radio.sh restart

# Check application status
./manage_radio.sh status
```

### Features

- **Automatic Port Management**: Checks and frees port 8000 if it's already in use
- **GPIO Daemon Check**: Ensures the pigpiod service is running
- **Process Management**: Properly handles process startup and shutdown
- **Status Monitoring**: Shows recent logs and current process status
- **Virtual Environment**: Automatically activates the Python virtual environment

### Troubleshooting

If the application fails to start:

1. **Check the Logs**:
   ```bash
   tail -f logs/radio.log
   ```

2. **Verify Port Availability**:
   ```bash
   sudo lsof -i :8000
   ```

3. **Check GPIO Daemon**:
   ```bash
   sudo systemctl status pigpiod
   ```

4. **Force Restart**:
   ```bash
   ./manage_radio.sh stop
   sleep 2
   ./manage_radio.sh start
   ```

### Common Issues

- If the application shows as "not running" but the port is in use, use the restart command
- If you see "stale PID file found", the application may have crashed - check the logs and restart
- If the GPIO controls aren't working, ensure pigpiod is running with the status command