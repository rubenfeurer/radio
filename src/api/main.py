from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List
from src.core.models import RadioStation, SystemStatus
from src.core.radio_manager import RadioManager

app = FastAPI(title="Internet Radio API")
radio_manager = RadioManager()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active WebSocket connections
active_connections: Dict[int, WebSocket] = {}

@app.get("/")
async def root():
    return {"status": "online", "message": "Internet Radio API is running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/stations/")
async def add_station(station: RadioStation):
    radio_manager.add_station(station)
    return {"message": "Station added successfully"}

@app.get("/stations/{slot}", response_model=RadioStation)
async def get_station(slot: int):
    station = radio_manager.get_station(slot)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    return station

@app.post("/stations/{slot}/play")
async def play_station(slot: int):
    station = radio_manager.get_station(slot)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    radio_manager.play_station(slot)
    await broadcast_status(radio_manager.get_status().model_dump())
    return {"message": "Playing station"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connection_id = id(websocket)
    active_connections[connection_id] = websocket
    
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "status_request":
                status = radio_manager.get_status()
                await websocket.send_json({
                    "type": "status_response",
                    "data": status.model_dump()
                })
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        if connection_id in active_connections:
            del active_connections[connection_id]