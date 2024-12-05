from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
from src.core.singleton_manager import RadioManagerSingleton
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
active_connections: Set[WebSocket] = set()

async def broadcast_status_update(status: dict):
    """Broadcast status to all connected clients"""
    logger.debug(f"Broadcasting status update to {len(active_connections)} clients")
    for connection in active_connections.copy():  # Use copy to avoid modification during iteration
        try:
            await connection.send_json({
                "type": "status_update",
                "data": status
            })
        except WebSocketDisconnect:
            logger.debug("Client disconnected during broadcast")
            active_connections.remove(connection)
        except Exception as e:
            logger.error(f"Error broadcasting to client: {str(e)}")
            active_connections.remove(connection)

# Get the singleton instance
radio_manager = RadioManagerSingleton.get_instance(status_update_callback=broadcast_status_update)

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    logger.info(f"New WebSocket connection. Total connections: {len(active_connections)}")
    
    try:
        # Send initial status
        status = radio_manager.get_status()
        status_dict = status.model_dump()
        
        await websocket.send_json({
            "type": "status_response",
            "data": status_dict
        })
        
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "status_request":
                status = radio_manager.get_status()
                status_dict = status.model_dump()
                await websocket.send_json({
                    "type": "status_response",
                    "data": status_dict
                })
            elif data.get("type") == "wifi_scan":
                networks = radio_manager.scan_wifi_networks()
                await websocket.send_json({
                    "type": "wifi_scan_result",
                    "data": networks
                })
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
        active_connections.remove(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        active_connections.remove(websocket)
