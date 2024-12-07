from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import stations, system, websocket, wifi, monitor
from src.core.singleton_manager import RadioManagerSingleton
from src.api.routes.websocket import broadcast_status_update
import socket
import logging

app = FastAPI(title="Internet Radio API")

# Initialize the singleton RadioManager with WebSocket callback
radio_manager = RadioManagerSingleton.get_instance(status_update_callback=broadcast_status_update)

# Get the hostname and add .local suffix for mDNS
hostname = f"{socket.gethostname()}.local"

# Construct the allowed origins
allowed_origins = [
    f"http://{hostname}:5173",    # Dev server
    f"http://{hostname}",         # Production
    f"ws://{hostname}",          # WebSocket production
    f"ws://{hostname}:80",       # WebSocket explicit port
    "http://localhost:5173",      # Local development
    "ws://localhost:80",         # Local WebSocket
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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

logger = logging.getLogger(__name__)

@app.get("/")
async def root():
    """
    Root endpoint that redirects to frontend
    """
    return RedirectResponse(url=f"http://{hostname}:5173")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    logger.error(f"Internal Server Error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error. Check server logs for details."}
    )

@app.get("/api/v1/")
async def root():
    return {"message": "Radio API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)