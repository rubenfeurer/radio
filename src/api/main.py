from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import stations, system, websocket, wifi, monitor
from src.core.singleton_manager import RadioManagerSingleton
from src.api.routes.websocket import broadcast_status_update
import socket
import logging
from fastapi import WebSocket, WebSocketDisconnect
from src.core.models import SystemStatus
from config.config import settings
import os

app = FastAPI(title="Internet Radio API")

# Initialize the singleton RadioManager with WebSocket callback
radio_manager = RadioManagerSingleton.get_instance(status_update_callback=broadcast_status_update)

# Get the hostname and add .local suffix for mDNS
hostname = f"{socket.gethostname()}.local"

# Construct the allowed origins using settings
allowed_origins = [
    f"http://{hostname}:{settings.DEV_PORT}",    # Dev server
    f"http://{hostname}",                        # Production
    f"ws://{hostname}",                          # WebSocket production
    f"ws://{hostname}:{settings.API_PORT}",      # WebSocket explicit port
    f"http://localhost:{settings.DEV_PORT}",     # Local development
    f"ws://localhost:{settings.API_PORT}",       # Local WebSocket
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with configured prefix
app.include_router(stations.router, prefix=settings.API_V1_STR)
app.include_router(system.router, prefix=settings.API_V1_STR)
app.include_router(wifi.router, prefix=settings.API_V1_STR)
app.include_router(websocket.router, prefix=settings.API_V1_STR)
app.include_router(monitor.router, prefix=settings.API_V1_STR)

# Mount the built frontend files
frontend_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "web/build")
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")
else:
    # In development, redirect to Vite dev server
    @app.get("/")
    async def root():
        """Redirect to dev server in development mode"""
        return RedirectResponse(url=f"http://{hostname}:{settings.DEV_PORT}")

    @app.get("/{path:path}")
    async def catch_all(path: str):
        """Forward all non-API requests to dev server"""
        if not path.startswith(settings.API_V1_STR.lstrip("/")):
            return RedirectResponse(url=f"http://{hostname}:{settings.DEV_PORT}/{path}")
        raise HTTPException(status_code=404, detail="Not found")

logger = logging.getLogger(__name__)

@app.get("/health", tags=["Health"])
@app.head("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.get(f"{settings.API_V1_STR}/health", tags=["Health"])
@app.head(f"{settings.API_V1_STR}/health", tags=["Health"])
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

@app.get(f"{settings.API_V1_STR}/", tags=["System"])
async def api_root():
    """Root API endpoint"""
    return {"message": "Radio API"}

@app.websocket(f"{settings.API_V1_STR}{settings.WS_PATH}")
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
    uvicorn.run(app, host="0.0.0.0", port=settings.API_PORT)
