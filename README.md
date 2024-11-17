Internet Radio for Raspberry Pi
=============================

A simple internet radio player for Raspberry Pi with GPIO button control and rotary encoder 
volume control. Play your favorite radio stations with physical buttons and manage them 
through configuration files.

Features
--------
* GPIO button control for 3 radio stations
* Rotary encoder for volume control
* Configurable rotation direction and volume step size
* Persistent station configuration via TOML
* Automatic service management with systemd
* Configurable radio stations
* Rotating log management
* Unit test coverage

Hardware Requirements
-------------------
* Raspberry Pi (tested on Pi 4)
* 3 push buttons connected to:
  - GPIO 23 (Button 1)
  - GPIO 24 (Button 2) 
  - GPIO 25 (Button 3)
* Rotary encoder connected to:
  - GPIO 11 (CLK)
  - GPIO 9 (DT)
  - GPIO 10 (SW)
* Speakers/Audio output

Installation
-----------
1. Clone the repository:
   git clone https://github.com/yourusername/internetRadio.git
   cd internetRadio

2. Make installation scripts executable:
   chmod +x scripts/*.sh

3. Run the installation script:
   sudo ./scripts/install.sh

Service Management
----------------
The radio runs as a systemd service. Common commands:

Start the service:
sudo systemctl start radio

Stop the service:
sudo systemctl stop radio

Restart the service:
sudo systemctl restart radio

Check service status:
sudo systemctl status radio

View logs:
journalctl -u radio -f

Enable service to start on boot:
sudo systemctl enable radio

Configuration
------------
The rotary encoder behavior can be customized in config/config.toml:

[rotary.settings]
volume_step = 5              # Volume change per rotation step (1-100)
double_click_timeout = 500   # Double click timeout in milliseconds
debounce_time = 50          # Debounce time for button in milliseconds
clockwise_increases = true   # When true, clockwise rotation increases volume

Testing
-------
Run unit tests:

Run all tests:
python3 -m pytest tests/

Run tests with verbose output:
python3 -m pytest tests/ -v

Run specific test file with verbose output:
python3 -m pytest tests/test_gpio_handler.py -v
python3 -m pytest tests/test_stream_manager.py -v
python3 -m pytest tests/test_radio_player.py -v
python3 -m pytest tests/test_radio_service.py -v
python3 -m pytest tests/test_rotary_handler.py -v

The verbose output (-v flag) shows:
- Individual test case names
- Pass/Fail status for each test
- Test execution time
- Detailed error messages for failed tests

Troubleshooting
--------------
Audio Issues:
1. Check ALSA device configuration:
   aplay -l

2. Verify volume levels:
   amixer -c 2

Service Issues:
1. Check service status:
   sudo systemctl status radio

2. View detailed logs:
   journalctl -u radio -f

Rotary Encoder Issues:
1. Check GPIO pin connections
2. Verify config.toml settings
3. Check logs for rotation detection
4. Try reversing clockwise_increases setting if direction is wrong

Uninstallation
-------------
To remove the application:
sudo ./scripts/uninstall.sh

Contributing
-----------
1. Fork the repository
2. Create a feature branch
3. Write tests for new features
4. Ensure all tests pass
5. Create a Pull Request

License
-------
[Your License Here]