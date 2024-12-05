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
├── src/            # Source code
│   ├── api/        # API endpoints
│   ├── core/       # Business logic
│   ├── hardware/   # Hardware interfaces
│   ├── system/     # System management
│   └── utils/      # Utility functions
├── tests/          # Test files
├── web/            # Web Interface (SvelteKit)
│   ├── src/        # SvelteKit source code
│   ├── static/     # Static assets
│   ├── package.json
│   └── ...         # Other SvelteKit files
├── venv/           # Virtual environment
└── README.md       # This file
```

## Web Interface Setup

The web interface is built using SvelteKit and Flowbite-Svelte components.

### Setup Instructions

1. **Navigate to the web directory**:
   ```bash
   cd ~/radio/web
   ```

2. **Initialize a new SvelteKit project**:
   ```bash
   npx create-svelte@latest .
   ```

3. **Select the following options**:
   - Template: Skeleton project
   - TypeScript: Yes, using TypeScript syntax
   - ESLint: Yes
   - Prettier: Yes
   - Playwright: Yes

4. **Install dependencies**:
   ```bash
   npm install
   npm install flowbite-svelte flowbite
   npm install -D tailwindcss postcss autoprefixer @sveltejs/adapter-static
   ```

5. **Configure Tailwind CSS**:
   - Create `tailwind.config.js` and `src/app.css` as described in the setup instructions.

6. **Run the development server**:
   ```bash
   npm run dev -- --open
   ```

### Features

- **Responsive Design**: Works on mobile, tablet, and desktop
- **Real-time Updates**: WebSocket connection for immediate feedback
- **Station Management**: Three configurable radio slots
- **Volume Control**: Both web and physical control sync
- **Status Indicators**: Clear visual feedback
- **Mobile-First**: Touch-friendly interface
- **No Installation**: Access via web browser
- **Easy URL**: Access via `http://radio.local`

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

## Testing

The project uses pytest for unit testing. Tests are located in the `/tests` directory.

### Setting Up Tests

1. **Activate Virtual Environment**:
   ```bash
   cd ~/radio
   source venv/bin/activate
   ```

2. **Install Required Test Packages**:
   ```bash
   pip install pytest
   pip install pytest-asyncio
   pip install pytest-cov
   ```

3. **Add Test Dependencies to requirements.txt**:
   ```bash
   echo "pytest" >> requirements.txt
   echo "pytest-asyncio" >> requirements.txt
   echo "pytest-cov" >> requirements.txt
   ```

### Running Tests

After installing the required packages, you can run tests using:

```bash
# Run all tests
PYTHONPATH=. pytest -v --asyncio-mode=auto tests/

# Run tests with hardware mocking (CI environment)
PYTHONPATH=. MOCK_HARDWARE=true pytest -v --asyncio-mode=auto tests/

# Run tests with coverage
PYTHONPATH=. MOCK_HARDWARE=true pytest -v --asyncio-mode=auto tests/ --cov=src
```

### Test Structure

```
tests/
├── api/              # API endpoint tests
│   ├── test_main.py
│   └── test_routes.py
├── core/             # Core functionality tests
│   ├── test_models.py
│   └── test_radio_manager.py
└── hardware/         # Hardware interface tests
    ├── test_audio_player.py
    └── test_gpio_controller.py
```

### Writing Tests

Tests are written using pytest and follow these conventions:
- Test files start with `test_`
- Test functions start with `test_`
- Async tests use `@pytest.mark.asyncio` decorator
- Fixtures are defined in `conftest.py` or test files

Example test:
```python
import pytest
from src.core.radio_manager import RadioManager
from src.core.models import RadioStation

@pytest.mark.asyncio
async def test_play_station():
    manager = RadioManager()
    station = RadioStation(name="Test", url="http://test.com", slot=1)
    manager.add_station(station)
    
    await manager.play_station(1)
    status = manager.get_status()
    
    assert status.is_playing == True
    assert status.current_station == 1
```

### Common Test Commands

```bash
# Run tests and show coverage
pytest --cov=src tests/

# Run tests matching a pattern
pytest -k "test_station"

# Run tests and stop on first failure
pytest -x tests/

# Run tests with debug logging
pytest --log-cli-level=DEBUG tests/
```

### Troubleshooting Tests

If tests fail:
1. Check the virtual environment is activated
2. Verify all test dependencies are installed
3. Check the log output for detailed error messages
4. Ensure the GPIO daemon (pigpiod) is running for hardware tests

### Hardware Mocking

The project uses a comprehensive mocking system for hardware components during testing:

1. **Environment Variables**:
   ```bash
   # Run tests with hardware mocking
   MOCK_HARDWARE=true pytest -v tests/
   
   # Or in CI environment (GitHub Actions)
   # Hardware mocking is automatically enabled
   ```

2. **Mock Configuration**:
   - MPV player for audio playback
   - pigpio for GPIO control
   - All hardware interactions are simulated
   - Defined in `tests/conftest.py`

3. **Testing Hardware Components**:
   ```python
   # Example test using hardware mocks
   @pytest.mark.asyncio
   async def test_audio_player(mock_hardware):
       player = AudioPlayer()
       await player.play("http://test.stream")
       mock_hardware['mpv'].play.assert_called_once()
   ```

4. **Local vs CI Testing**:
   ```bash
   # Local development (real hardware)
   pytest -v tests/
   
   # CI environment (mocked hardware)
   MOCK_HARDWARE=true pytest -v tests/
   ```

### Common Test Issues

- If hardware tests fail locally, ensure pigpiod is running:
  ```bash
  sudo systemctl start pigpiod
  ```
- For CI failures, verify MOCK_HARDWARE is set
- Check `tests/conftest.py` for mock configurations

## WebSocket API

The application provides real-time updates through WebSocket connections at `/ws`. This enables immediate feedback for physical controls and system status changes.

### Connecting to WebSocket

```javascript
// Browser example
const ws = new WebSocket('ws://your-pi-ip:8000/ws');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};
```

```python
# Python example using websockets
import asyncio
import websockets
import json

async def connect():
    async with websockets.connect('ws://your-pi-ip:8000/ws') as ws:
        # Send status request
        await ws.send(json.dumps({"type": "status_request"}))
        # Receive response
        response = await ws.recv()
        print(json.loads(response))
```

### Message Types

#### Client to Server:
1. **Status Request**
   ```json
   {
       "type": "status_request"
   }
   ```

2. **WiFi Scan Request**
   ```json
   {
       "type": "wifi_scan"
   }
   ```

#### Server to Client:
1. **Status Response/Update**
   ```json
   {
       "type": "status_response",
       "data": {
           "volume": 70,
           "current_station": 1,
           "is_playing": true,
           "wifi_status": "connected",
           "signal_strength": -67
       }
   }
   ```

2. **WiFi Scan Results**
   ```json
   {
       "type": "wifi_scan_result",
       "data": [
           {
               "ssid": "Network1",
               "signal_strength": -65,
               "secured": true
           }
       ]
   }
   ```

### Real-time Updates

The WebSocket connection automatically broadcasts:
- Volume changes from physical knob or web interface
- Station play/pause status changes
- WiFi connection status changes
- System mode changes (WiFi/AP mode)

### Error Handling

The WebSocket connection will automatically:
- Reconnect on disconnection
- Clean up resources on client disconnect
- Handle connection timeouts
- Report connection errors

### Example Usage

```javascript
// Complete browser example
const ws = new WebSocket('ws://your-pi-ip:8000/ws');

ws.onopen = function() {
    // Request initial status
    ws.send(JSON.stringify({
        type: "status_request"
    }));
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    switch(data.type) {
        case "status_response":
        case "status_update":
            updateUI(data.data);
            break;
        case "wifi_scan_result":
            updateNetworkList(data.data);
            break;
    }
};

ws.onerror = function(error) {
    console.error('WebSocket error:', error);
};

ws.onclose = function() {
    console.log('WebSocket connection closed');
    // Implement reconnection logic here
};
```

### Testing WebSocket Connection

You can test the WebSocket connection using the provided test suite:

```bash
# Run WebSocket-specific tests
pytest -v tests/api/test_routes.py -k "websocket"

# Run all API tests including WebSocket
pytest -v tests/api/
```