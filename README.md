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

### 1. Virtual Environment
```bash
# Create and activate virtual environment
cd ~/radio
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Web Interface Setup
```bash
cd ~/radio/web
npm install
npm install flowbite-svelte flowbite
npm install -D tailwindcss postcss autoprefixer @sveltejs/adapter-static
```

## Usage Modes

### Production Mode
```bash
# Build frontend
cd ~/radio/web
npm run build

# Start service
sudo systemctl start radio

# Access
http://radiod.local
```

### Development Mode
```bash
# Terminal 1: Frontend
cd ~/radio/web
npm run dev

# Terminal 2: Backend
cd ~/radio
DEV_MODE=true ./manage_radio.sh start

# Access
Frontend: http://<raspberry-pi-ip>:5173
API Docs: http://<raspberry-pi-ip>:80/docs
```

## Project Structure
```
radio/
├── src/
│   ├── api/        # FastAPI backend
│   ├── core/       # Business logic
│   ├── hardware/   # Hardware control
│   └── utils/      # Shared utilities
├── web/           # SvelteKit frontend
├── tests/         # Test suites
└── config/        # Configuration
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
```bash
# Run all tests
PYTHONPATH=. pytest -v tests/

# With hardware mocking
MOCK_HARDWARE=true pytest -v tests/

# Run specific tests
pytest -k "test_radio" tests/
```

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
- Development: `development-YYYYMMDD-commit`

### Finding Releases
- Production releases: GitHub Releases page
- Development builds: GitHub Actions artifacts
- Direct download: `https://github.com/rubenfeurer/radio/releases`