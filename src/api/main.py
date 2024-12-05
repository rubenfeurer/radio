from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import stations, system, websocket
from src.core.singleton_manager import RadioManagerSingleton
from src.api.routes.websocket import broadcast_status_update
import socket

app = FastAPI(title="Internet Radio API")

# Initialize the singleton RadioManager with WebSocket callback
radio_manager = RadioManagerSingleton.get_instance(status_update_callback=broadcast_status_update)

# Get the hostname and add .local suffix for mDNS
hostname = f"{socket.gethostname()}.local"

# Construct the allowed origins
allowed_origins = [
    f"http://{hostname}:5173",  # Dev server
    f"http://{hostname}",       # Root domain
    "http://localhost:5173",    # Local development
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
app.include_router(websocket.router)

@app.get("/")
async def root():
    return RedirectResponse(url=f"http://{hostname}:5173", status_code=307)