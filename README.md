# Internet Radio

A web-controlled internet radio system for Raspberry Pi with physical controls and WiFi management.

## Features

- Three configurable radio station slots with instant playback
- Physical controls (buttons and rotary encoder)
- Web interface with mobile support
- Real-time updates via WebSocket
- WiFi management with Access Point mode
- Volume control via knob and web interface
- System sounds for user feedback
- Hardware support for Raspberry Pi 4B and Zero 2 WH

## Quick Start

### Access the Radio

- Web Interface: `http://radiod.local`
- Default AP Mode: Connect to `RadioPi` network
- Direct IP: `http://<raspberry-pi-ip>`

### Basic Controls

- Play/Pause: Click station slot or use physical buttons
- Volume: Use rotary knob or web slider
- WiFi: Connect via web interface

## Development Setup

### Using Docker (Recommended)

```bash
# Start development environment (backend + frontend)
./dev.sh start

# Stop all services
./dev.sh stop

# View backend logs
./dev.sh logs

# Rebuild everything
./dev.sh rebuild
```

The development environment will be available at:

- Frontend: http://localhost:5173
- API Docs: http://localhost:80/docs
- Backend: http://localhost:80

### Manual Setup (Alternative)

#### 1. Virtual Environment

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### 2. Web Interface

```bash
cd web
npm install
npm run dev
```

## Project Structure

```
radio/
├── src/           # Backend source code
│   ├── api/       # FastAPI backend
│   ├── core/      # Business logic
│   ├── hardware/  # Hardware control
│   └── utils/     # Shared utilities
├── web/           # SvelteKit frontend
├── tests/         # Test suites
├── config/        # Configuration files
├── docker/        # Docker configuration
│   └── dev/       # Development containers
└── dev.sh        # Development script
```

## Configuration

### Radio Stations

Edit `config/stations.json`:

```json
{
  "stations": [
    {
      "name": "Station 1",
      "url": "http://stream.url",
      "slot": 1
    }
  ]
}
```

### System Settings

Edit `config/settings.json`:

```json
{
  "volume": {
    "default": 70,
    "knob_direction": "clockwise"
  },
  "ap_mode": {
    "ssid": "RadioPi",
    "password": "yourpassword"
  }
}
```

## Service Management

```bash
# Status
sudo systemctl status radio

# Logs
sudo journalctl -u radio -f

# Restart
sudo systemctl restart radio

# Stop
sudo systemctl stop radio
```

## Testing

### Using Docker (Recommended)

```bash
# Run tests in existing container (fast, for development)
./dev.sh test

# Run tests in clean container (for verification)
./dev.sh test-clean

# Common test options:
./dev.sh test --cov=src            # Run with coverage
./dev.sh test tests/test_wifi.py   # Run specific test file
./dev.sh test -k "test_wifi"       # Run tests matching pattern
./dev.sh test -v                   # Verbose output
```

All tests run with hardware mocking enabled (`MOCK_SERVICES=true`).

## Troubleshooting

### Common Issues

1. **Radio Not Starting**:

   ```bash
   tail -f logs/radio.log
   sudo lsof -i :80
   ```

2. **No Audio**:

   - Check volume settings
   - Verify audio device permissions
   - Restart audio service

3. **WiFi Issues**:
   - Check network status
   - Verify WiFi credentials
   - Switch to AP mode if needed

### GPIO Setup

```bash
# Install pigpio
sudo apt-get install pigpio python3-pigpio

# Start and enable service
sudo systemctl enable pigpiod
sudo systemctl start pigpiod

# Check status
sudo systemctl status pigpiod
```

## Development Resources

### API Documentation

- OpenAPI UI: `http://radiod.local/docs`
- ReDoc: `http://radiod.local/redoc`

### WebSocket Events

Connect to `ws://radiod.local/ws` for real-time updates:

- Volume changes
- Station status
- WiFi connection status
- System mode changes

## License

MIT License - See LICENSE file for details

## Installation

### Quick Install

1. Download latest release:

   ```bash
   wget https://github.com/rubenfeurer/radio/releases/latest/download/radio-v*.tar.gz
   ```

2. Extract and install:

   ```bash
   tar xzf radio-v*.tar.gz
   cd radio-*
   sudo ./install/install.sh
   ```

3. Access your radio at `http://radiod.local`

### Development Build

Latest development build can be downloaded from GitHub Actions:

1. Go to Actions tab
2. Select latest development workflow
3. Download artifact from bottom of page
4. Install as described above

## Release Process

### Creating a Production Release

1. Ensure all changes are merged to main
2. Create and push a new tag:
   ```bash
   git checkout main
   git pull
   git tag v1.0.0  # Update version number
   git push origin v1.0.0
   ```
3. GitHub Action will automatically:
   - Build frontend
   - Create release package
   - Publish to GitHub Releases

### Creating a Development Build

1. Push to development branch:
   ```bash
   git checkout development
   git push origin development
   ```
2. GitHub Action will automatically:
   - Build frontend
   - Create development package
   - Upload as workflow artifact

### Version Numbering

- Production: `v1.0.0`, `v1.0.1`, etc.
- Development: `develop-YYYYMMDD-commit`

### Finding Releases

- Production releases: GitHub Releases page
- Development builds: GitHub Actions artifacts
- Direct download: `https://github.com/rubenfeurer/radio/releases`
