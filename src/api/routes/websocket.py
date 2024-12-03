from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict
from src.core.radio_manager import RadioManager

router = APIRouter()
radio_manager = RadioManager()
active_connections: Dict[int, WebSocket] = {}

@router.websocket("/ws")
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
    except WebSocketDisconnect:
        del active_connections[connection_id]
