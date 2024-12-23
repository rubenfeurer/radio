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

### Singleton Implementation

The application uses a singleton pattern to ensure only one instance of `RadioManager` exists throughout the application lifecycle. This is crucial for:
- Preventing multiple GPIO controller initializations
- Maintaining consistent state across all routes
- Ensuring proper WebSocket callback handling

```python
# Using the singleton manager
from src.core.singleton_manager import SingletonRadioManager
from src.api.routes.websocket import broadcast_status_update

# Get the singleton instance with WebSocket callback
radio_manager = SingletonRadioManager.get_instance(status_update_callback=broadcast_status_update)
```

The singleton pattern is implemented in `src/core/singleton_manager.py` and should be used whenever accessing the `RadioManager` instead of creating new instances.

### Basic Usage

```python
from src.core.singleton_manager import SingletonRadioManager
from src.core.models import RadioStation

# Get the radio manager instance
radio = SingletonRadioManager.get_instance()

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
   pip install pytest-mock
   pip install httpx
   ```

3. **Add Test Dependencies to requirements.txt**:
   ```bash
   echo "pytest" >> requirements.txt
   echo "pytest-asyncio" >> requirements.txt
   echo "pytest-cov" >> requirements.txt
   echo "pytest-mock" >> requirements.txt
   echo "httpx" >> requirements.txt
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
- Use `pytest-mock` for mocking dependencies

Example test with mocking:
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

## API and WebSocket Development

### File Structure
```
radio/
├── src/
│   ├── api/            # Backend API
│   │   ├── routes/     # API route modules
│   │   │   ├── websocket.py  # WebSocket endpoints
│   │   │   ├── monitor.py    # Monitor endpoints
│   │   │   └── stations.py   # Station management endpoints
│   │   ├── models/     # API models and schemas
│   │   ��   └── requests.py   # Request/Response models
│   │   └── main.py    # FastAPI application setup
│   └── lib/           # Shared libraries
│       └── stores/    # Svelte stores
│           └── websocket.ts  # WebSocket store
└── web/
    └── src/
        └── routes/    # SvelteKit pages
            ├── +page.svelte        # Main page
            └── monitor/
                └── +page.svelte    # Monitor page
```

### WebSocket Store
The WebSocket store (`websocket.ts`) is currently located in `src/lib/stores/` and provides shared WebSocket functionality across the application. It manages:
- WebSocket connection status
- Monitor connection status
- Error handling

### Creating New API Endpoints

1. **Create Route Module**
   Create a new file in `src/api/routes/`:
   ```python:src/api/routes/example.py
   from fastapi import APIRouter
   from ..models.requests import ExampleModel
   
   router = APIRouter(
       prefix="/example",
       tags=["Example"]
   )
   
   @router.get("/status")
   async def get_status():
       return {"status": "ok"}
   ```

2. **Add Models**
   Define request/response models in `src/api/models/requests.py`:
   ```python:src/api/models/requests.py
   from pydantic import BaseModel
   
   class ExampleModel(BaseModel):
       name: str
       value: int
   ```

3. **Register Router**
   Add the router in `src/api/main.py`:
   ```python:src/api/main.py
   from src.api.routes import example
   
   app.include_router(example.router, prefix="/api/v1")
   ```

### WebSocket Communication

1. **Backend: Add New Message Type**
   Update `src/api/routes/websocket.py`:
   ```python:src/api/routes/websocket.py
   @router.websocket("/ws")
   async def websocket_endpoint(websocket: WebSocket):
       # ... existing code ...
       
       elif data.get("type") == "example_request":
           example_data = {
               "type": "example_update",
               "data": await get_example_data()
           }
           await websocket.send_json(example_data)
   ```

2. **Frontend: Handle WebSocket Messages**
   Create new page in `web/src/routes/`:
   ```svelte:web/src/routes/example/+page.svelte
   <script lang="ts">
     import { onMount } from 'svelte';
     import { browser } from '$app/environment';
   
     let ws: WebSocket;
     
     function connectWebSocket() {
       if (!browser) return;
       
       const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
       const wsHost = window.location.hostname;
       const wsPort = window.location.port === '5173' ? '80' : window.location.port;
       
       const wsUrl = `${wsProtocol}//${wsHost}${wsPort ? ':' + wsPort : ''}/api/v1/ws`;
       
       ws = new WebSocket(wsUrl);
       
       ws.onmessage = (event) => {
         const data = JSON.parse(event.data);
         if (data.type === 'example_update') {
           // Handle data
         }
       };
     }
   
     onMount(() => {
       connectWebSocket();
       return () => ws?.close();
     });
   </script>
   ```

### Message Types

Common WebSocket message types:

1. **Status Messages**
   ```typescript
   // Request
   { type: "status_request" }
   
   // Response
   {
     type: "status_response",
     data: {
       current_station: number | null,
       volume: number,
       is_playing: boolean
     }
   }
   ```

2. **Monitor Messages**
   ```typescript
   // Request
   { 
     type: "monitor_request",
     data: { requestType: "full" | "update" }
   }
   
   // Response
   {
     type: "monitor_update",
     data: {
       systemInfo: {...},
       services: [...],
       webAccess: {...},
       logs: [...]
     }
   }
   ```

### Best Practices
- Use consistent message types between frontend and backend
- Implement proper error handling in both directions
- Add logging for debugging
- Follow existing patterns in the codebase
- Keep WebSocket connections alive with periodic status checks
- Handle reconnection gracefully
- Clean up WebSocket connections when components unmount

## WiFi Management

### Features
- Network scanning and connection
- Saved network management
- Access Point (AP) mode support
- Real-time status updates via WebSocket
- Signal strength monitoring
- Automatic reconnection

### WiFi API Endpoints

1. **Get Available Networks**
   ```bash
   GET /api/v1/wifi/networks
   ```
   Returns list of available WiFi networks with signal strength and saved status.

2. **Connect to Network**
   ```bash
   POST /api/v1/wifi/connect
   {
     "ssid": "NetworkName",
     "password": "NetworkPassword"
   }
   ```

3. **Forget Network**
   ```bash
   DELETE /api/v1/wifi/forget/{ssid}
   ```
   Removes a saved network from the system.

4. **Get Current Status**
   ```bash
   GET /api/v1/wifi/status
   ```
   Returns current WiFi connection status.

### WiFi Manager

The `WiFiManager` class handles all WiFi-related operations:
```python
from src.core.wifi_manager import WiFiManager

# Get WiFi status
status = wifi_manager.get_current_status()

# Connect to network
success = await wifi_manager.connect_to_network("SSID", "password")

# Remove saved network
success = wifi_manager._remove_connection("SSID")
```

### Web Interface Features
- Display available networks with signal strength
- Show saved networks separately
- Connect to new networks
- Forget saved networks
- Real-time connection status
- Signal strength indicator

## Production vs Development Mode

### Production Mode
1. **Build the Frontend**:
   ```bash
   cd ~/radio/web
   npm run build
   ```
   This creates optimized files in `web/build/` that FastAPI will serve.

2. **Start the Radio Service**:
   ```bash
   sudo systemctl start radio
   ```

3. **Access the UI**:
   - Local network: `http://radiod.local`
   - Direct IP: `http://<raspberry-pi-ip>`
   - Default port: 80

4. **Service Management**:
   ```bash
   # Check status
   sudo systemctl status radio
   
   # View logs
   sudo journalctl -u radio -f
   
   # Restart service
   sudo systemctl restart radio
   
   # Stop service
   sudo systemctl stop radio
   ```

### Development Mode
1. **Start Frontend Dev Server**:
   ```bash
   cd ~/radio/web
   npm run dev
   ```

2. **Start Backend with Hot Reload**:
   ```bash
   # In another terminal
   cd ~/radio
   DEV_MODE=true ./manage_radio.sh start
   ```

3. **Access Development UI**:
   - Frontend: `http://<raspberry-pi-ip>:5173`
   - Backend API: `http://<raspberry-pi-ip>:80`
   - API Docs: `http://<raspberry-pi-ip>:80/docs`

4. **Development Features**:
   - Hot reload for frontend changes
   - Auto-reload for backend changes
   - Detailed logging
   - API documentation available

### Building for Production

1. **Build Frontend**:
   ```bash
   cd ~/radio/web
   
   # Install dependencies
   npm install
   
   # Create production build
   npm run build
   ```

2. **Verify Build**:
   - Check `web/build/` directory for output files
   - Test the build locally before deploying

3. **Deploy to Production**:
   ```bash
   # Stop the service
   sudo systemctl stop radio
   
   # Start in production mode
   sudo systemctl start radio
   ```

### Finding Your Radio on the Network

1. **Using mDNS**:
   - Default URL: `http://radiod.local`
   - Works on most modern devices without configuration

2. **Using IP Address**:
   ```bash
   # Find IP address
   hostname -I
   
   # Or use
   ip addr show wlan0
   ```
   Then access: `http://<ip-address>`

3. **Port Usage**:
   - Production: Port 80 (default HTTP)
   - Development Frontend: Port 5173
   - Development Backend: Port 80

### Switching Between Modes

1. **Switch to Development**:
   ```bash
   # Stop production service
   sudo systemctl stop radio
   
   # Start in dev mode
   DEV_MODE=true ./manage_radio.sh start
   ```

2. **Switch to Production**:
   ```bash
   # Stop dev servers
   ./manage_radio.sh stop
   
   # Start production service
   sudo systemctl start radio
   ```
