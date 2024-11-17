# Internet Radio for Raspberry Pi

A simple internet radio player for Raspberry Pi with GPIO button control. Play your favorite radio stations with physical buttons and manage them through configuration files.

## Features

- GPIO button control for 3 radio stations
- Persistent station configuration via TOML
- Automatic service management with systemd
- Configurable radio stations
- Rotating log management
- Unit test coverage

## Hardware Requirements

- Raspberry Pi (tested on Pi 4)
- 3 push buttons connected to:
  - GPIO 17 (Button 1)
  - GPIO 16 (Button 2) 
  - GPIO 26 (Button 3)
- Speakers/Audio output

## Installation

1. Clone the repository:
git clone https://github.com/yourusername/internetRadio.git
cd internetRadio

2. Make installation scripts executable:
chmod +x scripts/*.sh

3. Run the installation script:
sudo ./scripts/install.sh

## Service Management

The radio runs as a systemd service. Common commands:

# Start the service
sudo systemctl start radio

# Stop the service
sudo systemctl stop radio

# Restart the service
sudo systemctl restart radio

# Check service status
sudo systemctl status radio

# View logs
journalctl -u radio -f

# Enable service to start on boot
sudo systemctl enable radio

# Disable service from starting on boot
sudo systemctl disable radio

## Project Structure

internetRadio/
├── src/                    # Source code
│   ├── hardware/          # Hardware control
│   │   └── gpio_handler.py # GPIO button handling
│   ├── player/            # Radio player implementation
│   │   └── radio_player.py
│   └── utils/             # Utility modules
│       └── stream_manager.py  # Stream configuration
├── config/                # Configuration files
│   ├── streams.toml      # Radio station definitions
│   └── radio_state.json  # Current state
├── logs/                 # Application logs
├── scripts/              # Installation scripts
├── tests/                # Unit tests
└── systemd/              # Service configuration

## Dependencies

### System Dependencies:
- python3: Runtime environment
- vlc: Media player backend
- alsa-utils: Audio system utilities
- git: Version control

### Python Dependencies:
- python-vlc: VLC media player bindings
- tomli: TOML file parsing
- pytest: Testing framework

## Configuration

### Radio Stations
Configure radio stations in config/streams.toml:

[[links]]
name = "Station Name"
url = "http://stream.url"
country = "Country"
location = "City"

### Button Configuration
Buttons are mapped to the first three stations in radio_state.json:
- Button 1 (GPIO 17) -> First station
- Button 2 (GPIO 16) -> Second station
- Button 3 (GPIO 26) -> Third station

## Testing

Run unit tests:

# Run all tests
python3 -m pytest tests/

# Run tests with verbose output
python3 -m pytest tests/ -v

# Run specific test file with verbose output
python3 -m pytest tests/test_gpio_handler.py -v
python3 -m pytest tests/test_stream_manager.py -v
python3 -m pytest tests/test_radio_player.py -v
python3 -m pytest tests/test_radio_service.py -v

The verbose output (-v flag) shows:
- Individual test case names
- Pass/Fail status for each test
- Test execution time
- Detailed error messages for failed tests

## Troubleshooting

### Audio Issues:
1. Check ALSA device configuration:
aplay -l

2. Verify volume levels:
amixer -c 2

### Service Issues:
1. Check service status:
sudo systemctl status radio

2. View detailed logs:
journalctl -u radio -f

## Uninstallation

To remove the application:
sudo ./scripts/uninstall.sh

## Contributing

1. Fork the repository
2. Create a feature branch
3. Write tests for new features
4. Ensure all tests pass
5. Create a Pull Request

## License

[Your License Here]