import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.core.singleton_manager import RadioManagerSingleton

from .monitor import (
    check_web_access,
    get_recent_logs,
    get_services_status,
    get_system_info,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])
active_connections: set[WebSocket] = set()


async def broadcast_status_update(status: dict):
    """Broadcast status to all connected clients"""
    logger.debug(f"Broadcasting status update to {len(active_connections)} clients")
    for connection in active_connections.copy():
        try:
            await connection.send_json({"type": "status_update", "data": status})
        except WebSocketDisconnect:
            logger.debug("Client disconnected during broadcast")
            active_connections.remove(connection)
        except Exception as e:
            logger.error(f"Error broadcasting to client: {e!s}")
            active_connections.remove(connection)


radio_manager = RadioManagerSingleton.get_instance(
    status_update_callback=broadcast_status_update,
)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    logger.info(
        f"New WebSocket connection. Total connections: {len(active_connections)}",
    )

    try:
        # Send initial status
        status = radio_manager.get_status()
        status_dict = status.model_dump()

        await websocket.send_json({"type": "status_response", "data": status_dict})

        while True:
            data = await websocket.receive_json()
            logger.debug(f"Received WebSocket message: {data}")

            if data.get("type") == "status_request":
                status = radio_manager.get_status()
                status_dict = status.model_dump()
                await websocket.send_json(
                    {"type": "status_response", "data": status_dict},
                )
            elif data.get("type") == "wifi_scan":
                networks = radio_manager.scan_wifi_networks()
                await websocket.send_json(
                    {"type": "wifi_scan_result", "data": networks},
                )
            elif data.get("type") == "monitor_request":
                logger.info("Received monitor request")
                try:
                    system_info = await get_system_info()
                    services_status = await get_services_status()
                    web_access = await check_web_access()
                    logs = await get_recent_logs()

                    monitor_data = {
                        "type": "monitor_update",
                        "data": {
                            "systemInfo": (
                                system_info.dict()
                                if hasattr(system_info, "dict")
                                else system_info
                            ),
                            "services": services_status,
                            "webAccess": web_access,
                            "logs": logs,
                        },
                    }
                    logger.info(f"Sending monitor data: {monitor_data}")
                    await websocket.send_json(monitor_data)
                except Exception as e:
                    logger.error(
                        f"Error processing monitor request: {e!s}",
                        exc_info=True,
                    )
                    # Send error response to client
                    await websocket.send_json(
                        {"type": "monitor_error", "data": {"error": str(e)}},
                    )

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
        active_connections.remove(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e!s}")
        active_connections.remove(websocket)
