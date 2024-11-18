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

Dependencies
-----------
Core:
- python-vlc: Media playback
- RPi.GPIO: Hardware interface
- Flask: Web API
- toml/tomli: Configuration parsing

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