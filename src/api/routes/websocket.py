from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
from src.core.radio_manager import RadioManager
from src.core.models import SystemStatus

router = APIRouter()
radio_manager = RadioManager()
active_connections: Set[WebSocket] = set()

async def broadcast_status(status: dict):
    """Broadcast status to all connected clients"""
    for connection in active_connections:
        try:
            await connection.send_json({
                "type": "status_update",
                "data": status
            })
        except WebSocketDisconnect:
            active_connections.remove(connection)

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    
    try:
        # Send initial status
        status = radio_manager.get_status()
        await websocket.send_json({
            "type": "status_response",
            "data": status.model_dump()
        })
        
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "status_request":
                status = radio_manager.get_status()
                await websocket.send_json({
                    "type": "status_response",
                    "data": status.model_dump()
                })
            elif data.get("type") == "wifi_scan":
                networks = radio_manager.scan_wifi_networks()
                await websocket.send_json({
                    "type": "wifi_scan_result",
                    "data": networks
                })
    except WebSocketDisconnect:
        active_connections.remove(websocket)
