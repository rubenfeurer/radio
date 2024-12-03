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
├── src/           # Source code
│   ├── api/       # API endpoints
│   ├── core/      # Business logic
│   ├── hardware/  # Hardware interfaces
│   ├── system/    # System management
│   └── utils/     # Utility functions
├── tests/         # Test files
├── venv/          # Virtual environment
└── README.md      # This file
```

## API Endpoints

- `GET /`: Check if API is running
  - Response: `{"status": "online", "message": "Internet Radio API is running"}`

- `GET /health`: System health check
  - Response: `{"status": "healthy"}`

- `POST /stations/{slot}/play`: Play a specific radio station by slot
  - Request: `{ "slot": 1 }`
  - Response: `{ "message": "Playing station" }`

- `GET /volume`: Get the current volume level
  - Response: `{ "volume": 70 }`

- `POST /volume`: Set the volume level
  - Request: `{ "volume": 50 }`
  - Response: `{ "message": "Volume set successfully" }`

## Configuration

- **Hardware Pins**: Configurable in `config.py`
- **Volume Behavior**: Adjust sensitivity and default settings in `config.py`

## Development Notes

- The server runs in development mode with auto-reload enabled
- API documentation is automatically generated at `/docs`
- CORS is enabled for all origins in development mode