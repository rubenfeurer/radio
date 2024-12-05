from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import stations, system, websocket
from src.core.singleton_manager import SingletonRadioManager
from src.api.routes.websocket import broadcast_status_update
import socket

app = FastAPI(title="Internet Radio API")

# Initialize the singleton RadioManager with WebSocket callback
radio_manager = SingletonRadioManager.get_instance(status_update_callback=broadcast_status_update)

# Get the hostname
hostname = socket.gethostname()
# Construct the allowed origin using the hostname
allowed_origin = f"http://{hostname}:5173"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
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
    return {"status": "online", "message": "Internet Radio API is running"}