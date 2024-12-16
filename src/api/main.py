from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import stations, system, websocket, wifi, monitor
from src.core.singleton_manager import RadioManagerSingleton
from src.api.routes.websocket import broadcast_status_update
from src.core.wifi_manager import WiFiManager
from src.core.mode_manager import mode_manager
from src.utils.logger import logger
import socket
import logging
from fastapi import WebSocket, WebSocketDisconnect
from src.core.models import SystemStatus, NetworkMode
import asyncio

app = FastAPI(title="Internet Radio API")

# Initialize WiFiManager with skip_verify=True for testing
wifi_manager = WiFiManager(skip_verify=True)

# Initialize the singleton RadioManager with WebSocket callback
radio_manager = RadioManagerSingleton.get_instance(status_update_callback=broadcast_status_update)

# Get the hostname and add .local suffix for mDNS
hostname = f"{socket.gethostname()}.local"
ip_address = socket.gethostbyname(socket.gethostname())

# Construct the allowed origins
allowed_origins = [
    f"http://{hostname}:5173",    # Dev server with mDNS
    f"http://{hostname}",         # Production with mDNS
    f"ws://{hostname}",          # WebSocket with mDNS
    f"ws://{hostname}:80",       # WebSocket explicit port with mDNS
    f"http://{ip_address}:5173", # Dev server with IP
    f"http://{ip_address}",      # Production with IP
    f"ws://{ip_address}",       # WebSocket with IP
    f"ws://{ip_address}:80",    # WebSocket explicit port with IP
    "http://localhost:5173",     # Local development
    "ws://localhost:80",        # Local WebSocket
    "http://192.168.4.1:5173", # AP mode access
    "ws://192.168.4.1:80",     # AP mode WebSocket
    "*",                        # Allow all origins (for development)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_origin_regex="http://.*:5173"  # Allow any host on port 5173
)

# Include routers
app.include_router(stations.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")
app.include_router(wifi.router, prefix="/api/v1")
app.include_router(websocket.router, prefix="/api/v1")
app.include_router(monitor.router, prefix="/api/v1")

logger = logging.getLogger(__name__)

@app.get("/")
async def root(request: Request):
    """
    Root endpoint that redirects to frontend
    """
    # Try to get the client's requested host
    request_host = request.headers.get("host", "").split(":")[0]
    
    # If it's an IP address, use that, otherwise use hostname.local
    if request_host and not request_host.endswith('.local'):
        redirect_host = request_host
    else:
        redirect_host = f"{socket.gethostname()}.local"
    
    # Always redirect to port 5173 for development server
    return RedirectResponse(url=f"http://{redirect_host}:5173")

@app.get("/health", tags=["Health"])
@app.head("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.get("/api/v1/health", tags=["Health"])
@app.head("/api/v1/health", tags=["Health"])
async def api_health_check():
    """API Health check endpoint"""
    return {"status": "healthy"}

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal Server Error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error. Check server logs for details."}
    )

@app.get("/api/v1/", tags=["System"])
async def root():
    """Root API endpoint"""
    return {"message": "Radio API"}
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "status_request":
                status = radio_manager.get_status()
                status_dict = SystemStatus(
                    current_station=status.current_station.model_dump() if status.current_station else None,
                    volume=status.volume,
                    is_playing=status.is_playing
                ).model_dump()
                
                await websocket.send_json({
                    "type": "status_response",
                    "data": status_dict
                })
            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass

@app.on_event("startup")
async def startup_event():
    """Initialize application state"""
    try:
        logger.debug("Debug test message")
        logger.info("Starting up application...")
        
        # Verify required services
        logger.info("Verifying required services...")
        services = {
            'NetworkManager': await mode_manager._run_command(['systemctl', 'is-active', 'NetworkManager']),
            'wpa_supplicant': await mode_manager._run_command(['systemctl', 'is-active', 'wpa_supplicant']),
            'hostapd': await mode_manager._run_command(['systemctl', 'is-active', 'hostapd']),
            'dnsmasq': await mode_manager._run_command(['systemctl', 'is-active', 'dnsmasq'])
        }
        for service, status in services.items():
            logger.info(f"{service} status: {status.stdout.strip()}")
        
        # Force client mode on startup without temporary timeout
        logger.info("Forcing client mode on startup...")
        success = await mode_manager.force_client_mode()
        if not success:
            logger.error("Failed to switch to client mode")
            return
        
        # Wait for network
        logger.info("Waiting for network connectivity...")
        for _ in range(10):  # Try for 10 seconds
            try:
                await mode_manager._run_command(['ping', '-c', '1', '8.8.8.8'])
                logger.info("Network connectivity verified")
                break
            except:
                await asyncio.sleep(1)
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        logger.exception("Startup error details:")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=80)
