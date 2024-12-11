from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import stations, system, websocket, wifi, monitor, ap_mode
from src.core.singleton_manager import RadioManagerSingleton
from src.api.routes.websocket import broadcast_status_update
from src.api.routes.wifi import wifi_manager
import socket
import logging
from fastapi import WebSocket, WebSocketDisconnect
from src.core.models import SystemStatus

app = FastAPI(title="Internet Radio API")

# Initialize the singleton RadioManager with WebSocket callback
radio_manager = RadioManagerSingleton.get_instance(status_update_callback=broadcast_status_update)

# Get the hostname and add .local suffix for mDNS
hostname = f"{socket.gethostname()}.local"

# Construct the allowed origins
def get_allowed_origins():
    base_origins = [
        f"http://{hostname}:5173",    # Dev server
        f"http://{hostname}.local:5173",  # Add .local variant
        f"http://{hostname}",         # Production
        f"http://{hostname}.local",   # Add .local variant
        f"ws://{hostname}",          # WebSocket production
        f"ws://{hostname}:80",       # WebSocket explicit port
        "http://localhost:5173",      # Local development
        "ws://localhost:80",         # Local WebSocket
        "http://192.168.4.1",        # AP mode
        "http://192.168.4.1:5173",   # AP mode dev server
        "ws://192.168.4.1",          # AP mode WebSocket
        "ws://192.168.4.1:80",       # AP mode WebSocket explicit port
    ]
    try:
        return ["*"] if wifi_manager._check_ap_mode_active() else base_origins
    except:
        return base_origins  # Fallback to base origins if check fails

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(stations.router, prefix="/api/v1")
app.include_router(system.router, prefix="/api/v1")
app.include_router(wifi.router, prefix="/api/v1")
app.include_router(websocket.router, prefix="/api/v1")
app.include_router(monitor.router, prefix="/api/v1")
app.include_router(ap_mode.router, prefix="/api/v1")

logger = logging.getLogger(__name__)

@app.get("/")
async def root():
    """
    Root endpoint that redirects to frontend
    """
    return RedirectResponse(url=f"http://{hostname}:5173")

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
