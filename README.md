# Internet Radio

A web-controlled internet radio system for Raspberry Pi with physical controls and WiFi management.

## For Users

### Features

- Three configurable radio station slots with instant playback
- Physical controls (buttons and rotary encoder)
- Web interface with mobile support
- Real-time updates via WebSocket
- WiFi management with Access Point mode
- Volume control via knob and web interface
- System sounds for user feedback
- Hardware support for Raspberry Pi 4B and Zero 2 WH

### Installation

1. Download Latest Release:

   - Go to GitHub Releases page
   - Download the latest `radio-v*.tar.gz` file
   - Or use wget:

   ```bash
   wget https://github.com/user/radio/releases/latest/download/radio-v*.tar.gz
   ```

2. Install on Raspberry Pi:

   ```bash
   # Extract package
   tar -xzf radio-v*.tar.gz
   cd radio

   # Run installation script
   sudo ./install/install.sh

   # Wait for installation to complete
   # Radio service will start automatically
   ```

3. Verify Installation:
   - Check service status:
   ```bash
   sudo systemctl status radio
   ```

### Quick Start

#### Access the Radio User Interface

- Web Interface: `http://<hostname>.local`
- Default AP Mode: Connect to `<hostname>` network

#### Basic Controls

- Play/Pause: Click station slot or use physical buttons
- Volume: Use rotary knob or web slider
- WiFi: Connect via web interface

## For Developers

### Development Setup

#### On Raspberry Pi

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

#### Using Docker (Alternative)

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

#### Manual Setup (Alternative)

1. Virtual Environment:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Web Interface:
   ```bash
   cd web
   npm install
   npm run dev
   ```

### Project Structure

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

### Testing

#### Using Docker (Recommended)

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

### Development Resources

#### API Documentation

- OpenAPI UI: `http://radiod.local/docs`
- ReDoc: `http://radiod.local/redoc`

#### WebSocket Events

Connect to `ws://radiod.local/ws` for real-time updates:

- Volume changes
- Station status
- WiFi connection status
- System mode changes

### Development Workflow

#### 1. Feature Branch Development

- Create feature branch from `develop`
- Push changes trigger `branch-test.yml`
- Tests run automatically on push
- Pre-commit hooks ensure code quality

#### 2. Development Release

- Open PR to `develop` branch
- Tests run via `branch-test.yml`
- When merged, `dev-release.yml`:
  - Builds frontend
  - Creates development package
  - Tests installation
  - Uploads artifact

#### 3. Production Release

- Open PR from `develop` to `main`
- Tests run via `branch-test.yml`
- When merged, `prod-release.yml`:
  - Builds frontend
  - Creates production package
  - Tests in Pi environment
  - Creates GitHub release (for tags)

### Branch Protection

- Protected branches: `main`, `develop`
- Required status checks must pass
- No direct pushes allowed
- PRs required for all changes

### CI/CD Pipeline

#### Feature Branch Tests (`branch-test.yml`)

```bash
# Runs on:
- Push to feature branches
- PRs to main/develop
```

#### Development Release (`dev-release.yml`)

```bash
# Runs on:
- PR merge to develop
- Manual workflow dispatch
```

#### Production Release (`prod-release.yml`)

```bash
# Runs on:
- PR merge to main
- Version tags
- Manual workflow dispatch
```

### Configuration

#### Radio Stations

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

#### System Settings

Edit `config/config.py`:

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

### Service Management

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

### Troubleshooting

#### Common Issues

1. Radio Not Starting:

   ```bash
   tail -f logs/radio.log
   sudo lsof -i :80
   ```

2. No Audio:

   - Check volume settings
   - Verify audio device permissions
   - Restart audio service

3. WiFi Issues:
   - Check network status
   - Verify WiFi credentials
   - Switch to AP mode if needed

#### GPIO Setup

```bash
# Install pigpio
sudo apt-get install pigpio python3-pigpio

# Start and enable service
sudo systemctl enable pigpiod
sudo systemctl start pigpiod

# Check status
sudo systemctl status pigpiod
```

## License

MIT License - See LICENSE file for details
