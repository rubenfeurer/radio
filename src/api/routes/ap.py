from fastapi import APIRouter, HTTPException
from typing import List
import logging
from src.core.ap_manager import APManager, ConnectionError
from src.core.mode_manager import ModeManagerSingleton, NetworkMode
from src.core.models import WiFiNetwork, WiFiStatus
from src.api.models.requests import WiFiConnectionRequest, NetworkAddRequest
from pathlib import Path

router = APIRouter(prefix="/ap", tags=["Access Point"])
ap_manager = APManager()
logger = logging.getLogger(__name__)


@router.get("/networks", response_model=WiFiStatus)
async def get_saved_networks():
    """Get the last saved WiFi networks from before AP mode was enabled"""
    try:
        status = await ap_manager.get_saved_networks()
        if status is None:
            # Return empty status if no saved data
            return WiFiStatus(
                ssid=None,
                signal_strength=None,
                is_connected=False,
                has_internet=False,
                available_networks=[],
            )
        return status
    except Exception as e:
        logger.error(f"Error getting saved networks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/addconnection")
async def add_network_connection(request: NetworkAddRequest):
    """Add a new network connection while in AP mode"""
    try:
        result = await ap_manager.add_network_connection(
            request.ssid, request.password, request.priority
        )
        return result
    except Exception as e:
        logger.error(f"Error adding network connection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/modifyconnection")
async def modify_network_connection(request: NetworkAddRequest):
    """Modify an existing network connection while in AP mode"""
    try:
        result = await ap_manager.modify_network_connection(
            request.ssid, request.password, request.priority
        )
        return result
    except ConnectionError as e:
        # Map error types to appropriate HTTP status codes
        error_codes = {
            "mode_error": 400,  # Bad Request (wrong mode)
            "not_found_error": 404,  # Not Found (network doesn't exist)
            "connection_error": 503,  # Service Unavailable
            "unknown_error": 500,  # Internal Server Error
        }
        status_code = error_codes.get(e.error_type, 500)
        raise HTTPException(status_code=status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error modifying network connection: {e}")
        raise HTTPException(status_code=500, detail=str(e))
