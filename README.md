Internet Radio for Raspberry Pi
=============================

A Python-based internet radio player for Raspberry Pi that combines hardware control with 
software flexibility. The system uses GPIO buttons for station selection and a rotary encoder 
for volume control, managed through a modular architecture with clear separation of concerns.

Architecture Overview
-------------------
The project follows a modular design pattern with these key components:

1. Core Components:
   - RadioService (src/app/radio_service.py)
     * Main service coordinator
     * Manages component lifecycle
     * Handles initialization and cleanup
   
   - RadioPlayer (src/player/radio_player.py)
     * Manages VLC media player instance
     * Handles audio device detection
     * Controls volume and playback
     * Maintains player state
   
   - WiFiManager (src/utils/wifi_manager.py)
     * Manages WiFi connections using nmcli
     * Scans available networks
     * Handles connection/disconnection
     * Provides network status information

2. Hardware Interface:
   - GPIOHandler (src/hardware/gpio_handler.py)
     * Manages button inputs
     * Routes hardware events to appropriate handlers
     * Implements debouncing logic
   
   - RotaryHandler (src/hardware/rotary_handler.py)
     * Handles rotary encoder events
     * Manages volume control logic
     * Implements configurable rotation behavior

3. Utility Components:
   - StreamManager (src/utils/stream_manager.py)
     * Manages radio station configurations
     * Handles stream URL validation
     * Maintains station presets
   
   - SoundPlayer (src/utils/sound_player.py)
     * Handles system sound effects
     * Provides audio feedback for actions

4. Web Interface:
   - Flask Routes (src/app/routes.py)
     * Provides REST API endpoints
     * Enables remote control
     * Reports system status

5. Network Management:
   - WiFi Configuration
     * Web-based network selection
     * Password-protected connections
     * Current connection status
     * Signal strength monitoring
   - Connection Management
     * Automatic reconnection
     * Network scanning
     * Connection status monitoring

Directory Structure
-----------------
/internetRadio
├── src/
│   ├── app/
│   │   ├── radio_service.py
│   │   └── routes.py
│   ├── hardware/
│   │   ├── gpio_handler.py
│   │   └── rotary_handler.py
│   ├── player/
│   │   └── radio_player.py
│   └── utils/
│       ├── stream_manager.py
│       └── sound_player.py
├── tests/
│   ├── test_radio_player.py
│   ├── test_gpio_handler.py
│   └── ...
├── config/
│   ├── config.toml
│   └── streams.toml
└── scripts/
    ├── install.sh
    └── uninstall.sh

Technical Details
---------------
1. Audio System:
   - Uses ALSA for hardware audio control
   - VLC media player for stream playback
   - Supports multiple audio output devices
   - Volume control via hardware mixer

2. GPIO Interface:
   - Hardware debouncing for buttons
   - Interrupt-based rotary encoder handling
   - Configurable pin assignments
   - Event-driven architecture

3. Configuration Management:
   - TOML-based configuration
   - Persistent state storage
   - Runtime configuration updates
   - Default fallback values

4. Logging System:
   - Rotating log files
   - Configurable log levels
   - Systemd journal integration
   - Debug logging capabilities

API Endpoints
------------
All endpoints return JSON responses with at least `success` and `message` fields.

WiFi Management
-------------
1. Get WiFi Status
   ```
   GET /api/wifi/status
   Response: {
       "success": true,
       "current": {
           "ssid": "NetworkName",
           "signal": 90,
           "connected": true
       }
   }
   ```

2. Scan Networks
   ```
   GET /api/wifi/scan
   Response: {
       "success": true,
       "networks": [
           {
               "ssid": "NetworkName",
               "signal": 85,
               "security": "WPA2",
               "active": false,
               "saved": true
           },
           ...
       ]
   }
   ```

3. Connect to Network
   ```
   POST /api/wifi/connect
   Body: {
       "ssid": "NetworkName",
       "password": "NetworkPassword",  // Optional for saved networks
       "saved": true|false            // Optional, default false
   }
   Response: {
       "success": true,
       "message": "Successfully connected to NetworkName"
   }
   ```

4. Disconnect from Network
   ```
   POST /api/wifi/disconnect
   Response: {
       "success": true,
       "message": "Disconnected from NetworkName"
   }
   ```

5. Forget Network
   ```
   POST /api/wifi/forget
   Body: {
       "ssid": "NetworkName"
   }
   Response: {
       "success": true,
       "message": "Successfully removed network NetworkName"
   }
   ```

Radio Control
------------
1. Get Player Status
   ```
   GET /api/radio/status
   Response: {
       "success": true,
       "status": {
           "playing": true|false,
           "current_stream": "Stream Name",
           "volume": 75
       }
   }
   ```

2. Control Volume
   ```
   POST /api/radio/volume
   Body: {
       "volume": 75,  // 0-100
       "action": "set|up|down"  // Optional, default "set"
   }
   Response: {
       "success": true,
       "volume": 75
   }
   ```

3. Control Playback
   ```
   POST /api/radio/control
   Body: {
       "action": "play|stop|toggle",
       "stream_id": "1"  // Required for "play" action
   }
   Response: {
       "success": true,
       "message": "Now playing: Stream Name"
   }
   ```

Stream Management
---------------
1. Get Available Streams
   ```
   GET /api/streams
   Response: {
       "success": true,
       "streams": [
           {
               "id": "1",
               "name": "Stream Name",
               "url": "http://stream.url",
               "slot": 1
           },
           ...
       ]
   }
   ```

2. Update Stream
   ```
   POST /api/streams/update
   Body: {
       "id": "1",
       "name": "New Name",
       "url": "http://new.url",
       "slot": 2
   }
   Response: {
       "success": true,
       "message": "Stream updated successfully"
   }
   ```

Error Responses
-------------
All endpoints may return error responses in this format:
```
{
    "success": false,
    "message": "Error description"
}
```

Common error codes:
- 400: Bad Request (missing or invalid parameters)
- 404: Not Found (endpoint or resource not found)
- 500: Internal Server Error

Usage Examples
------------
1. Connect to a new WiFi network:
```bash
curl -X POST http://your-pi-ip:5000/api/wifi/connect \
     -H "Content-Type: application/json" \
     -d '{"ssid": "MyNetwork", "password": "MyPassword"}'
```

2. Connect to a saved network:
```bash
curl -X POST http://your-pi-ip:5000/api/wifi/connect \
     -H "Content-Type: application/json" \
     -d '{"ssid": "MyNetwork", "saved": true}'
```

3. Set volume:
```bash
curl -X POST http://your-pi-ip:5000/api/radio/volume \
     -H "Content-Type: application/json" \
     -d '{"volume": 75}'
```

4. Play a stream:
```bash
curl -X POST http://your-pi-ip:5000/api/radio/control \
     -H "Content-Type: application/json" \
     -d '{"action": "play", "stream_id": "1"}'
```

Dependencies
-----------
Core:
- python-vlc: Media playback
- RPi.GPIO: Hardware interface
- Flask: Web API
- toml/tomli: Configuration parsing
- NetworkManager: WiFi management (nmcli)

Development:
- pytest: Testing framework
- pytest-mock: Mocking for tests

Hardware Requirements
-------------------
* Raspberry Pi (tested on Pi 4)
* 3 push buttons:
  - GPIO 23 (Button 1)
  - GPIO 24 (Button 2) 
  - GPIO 25 (Button 3)
* Rotary encoder:
  - GPIO 11 (CLK)
  - GPIO 9 (DT)
  - GPIO 10 (SW)
* Audio output device

Installation and Setup
--------------------
[Previous installation instructions remain the same]

Testing Strategy
--------------
1. Unit Tests:
   - Component isolation
   - Mock hardware interfaces
   - Configuration validation
   - Error handling verification

   Mock Dependencies and Patterns:
   - unittest.mock (patch, MagicMock): Core mocking functionality
   - pytest-mock: Fixture-based mocking
   
   Common Mocking Patterns:
   a) Hardware Interface Mocks:
      ```python
      @pytest.fixture
      def mock_gpio():
          with patch('RPi.GPIO') as mock:
              yield mock
      ```
   
   b) Subprocess Calls:
      ```python
      @pytest.fixture
      def mock_subprocess():
          with patch('subprocess.run') as mock:
              yield mock
      ```
   
   c) File Operations:
      ```python
      @pytest.fixture
      def mock_open():
          with patch('builtins.open') as mock:
              yield mock
      ```
   
   d) Class-based Test Structure:
      ```python
      class TestComponent:
          @pytest.fixture
          def setup_component(self):
              with patch('dependency') as mock:
                  yield mock
      ```

   Component-Specific Patterns:
   - RadioPlayer: Mocks VLC instance and audio device detection
   - GPIOHandler: Mocks GPIO input/output and interrupt handling
   - StreamManager: Mocks file operations and URL validation
   - SoundPlayer: Mocks audio playback and device access
   - WiFiManager: Mocks nmcli subprocess calls

   Best Practices:
   - Use fixtures for common mock setups
   - Mock at the lowest possible level
   - Verify mock calls and interactions
   - Test error cases and edge conditions
   - Maintain isolation between tests
   - Use descriptive test names
   - Follow arrange-act-assert pattern

2. Integration Tests:
   - Component interaction
   - Hardware simulation
   - Audio subsystem testing
   - State management

3. System Tests:
   - End-to-end functionality
   - Performance monitoring
   - Resource management
   - Error recovery

Development Guidelines
--------------------
1. Code Style:
   - PEP 8 compliance
   - Type hints where applicable
   - Comprehensive docstrings
   - Clear error messages

2. Testing:
   - Test-driven development
   - Minimum 80% coverage
   - Mock external dependencies
   - Validate edge cases

3. Documentation:
   - Update README for new features
   - Document configuration options
   - Maintain API documentation
   - Include usage examples

[Previous troubleshooting and management sections remain the same]

Contributing
-----------
[Previous contributing guidelines remain the same]

License
-------
[License information]

Open TODOs
----------
1. Testing:
   - [ ] Add unit tests for SoundPlayer
   - [ ] Add integration tests for RotaryHandler
   - [ ] Add system tests for RadioService
   - [ ] Add stress tests for GPIO handling
   - [ ] Add network failure recovery tests
   - [ ] Add mock tests for audio subsystem
   - [ ] Add configuration validation tests

2. Features:
   - [ ] Implement station search functionality
   - [ ] Add network status indicator
   - [ ] Implement station metadata display

3. Documentation:
   - [ ] Add API documentation
   - [ ] Add hardware setup guide
   - [ ] Add troubleshooting guide
   - [ ] Add development setup guide
   - [ ] Document test coverage requirements