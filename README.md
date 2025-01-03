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

### On Raspberry Pi

1. Download development build:

   ```bash
   # From GitHub Actions:
   # Go to: GitHub -> Actions -> Build and Release -> Latest develop branch run
   # Download the "radio-dev-package" artifact

   tar -xzf radio-develop-*.tar.gz
   cd radio-*
   ```

2. Install and start development environment:

   ```bash
   # Install with development mode
   sudo DEV_MODE=true ./install/install.sh --dev

   # Start development environment
   ./dev.sh start   # Sets up everything automatically
   ```

Available development commands:

```bash
./dev.sh logs      # View backend logs
./dev.sh test      # Run tests
./dev.sh lint      # Check code quality
./dev.sh fix       # Auto-fix code issues
./dev.sh stop      # Stop all services
./dev.sh rebuild   # Rebuild environment
```

### Using Docker (Alternative)

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
# Run linting checks
./dev.sh lint

# Run tests in existing container (fast, for development)
./dev.sh test

# Run tests in clean container (for verification)
./dev.sh test-clean

# Run both linting and tests (recommended before committing)
./dev.sh test-all

# Common test options:
./dev.sh test --cov=src            # Run with coverage
./dev.sh test tests/test_wifi.py   # Run specific test file
./dev.sh test -k "test_wifi"       # Run tests matching pattern
./dev.sh test -v                   # Verbose output
```

All tests run with hardware mocking enabled (`MOCK_SERVICES=true`).

### Linting

The project uses several linting tools to maintain code quality:

- **Black**: Code formatting
- **Ruff**: Fast Python linter
- **MyPy**: Static type checking
- **Pylint**: Code analysis

Run all linting checks with:

```bash
./dev.sh lint
```

These are the same checks that run in the CI pipeline.

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

### Quick Install (Production)

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

### Development Installation

1. Download development build:

   ```bash
   # Option 1: Direct download from GitHub Actions
   # Go to: GitHub -> Actions -> Build and Release -> Latest develop branch run
   # Download the "radio-dev-package" artifact

   # Option 2: Using wget (replace URL with actual artifact URL)
   wget https://github.com/rubenfeurer/radio/actions/artifacts/radio-dev-package.zip
   unzip radio-dev-package.zip
   ```

2. Install with development flags:

   ```bash
   # Extract the package
   tar -xzf radio-develop-*.tar.gz
   cd radio-*

   # Full development installation
   sudo DEV_MODE=true ./install.sh --dev

   # For testing without hardware
   sudo DEV_MODE=true SKIP_HARDWARE=1 ./install.sh --dev
   ```

3. Verify installation:

   ```bash
   # Check service status
   systemctl status radio

   # Check version (should show development version)
   radio --version

   # View debug logs
   journalctl -u radio -f
   ```

4. Development features:

   - Debug logging enabled
   - Pre-commit hooks installed
   - Development dependencies available
   - Test suite installed
   - Source maps included

5. Running tests:

   ```bash
   # Activate virtual environment
   source /home/radio/radio/venv/bin/activate

   # Run tests
   pytest tests/

   # Run with coverage
   pytest --cov=src tests/
   ```

6. Development tools:

   ```bash
   # Format code
   black src/

   # Run linting
   ruff check src/

   # Type checking
   mypy src/
   ```

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
