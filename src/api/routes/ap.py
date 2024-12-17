from fastapi import APIRouter, HTTPException
from typing import List
import logging
from src.core.ap_manager import APManager, ConnectionError
from src.core.mode_manager import ModeManagerSingleton, NetworkMode
from src.core.models import WiFiNetwork
from src.api.models.requests import WiFiConnectionRequest

router = APIRouter(prefix="/ap", tags=["Access Point"])
ap_manager = APManager()
logger = logging.getLogger(__name__)

@router.post("/scan", response_model=List[WiFiNetwork])
async def scan_networks():
    """Scan for available WiFi networks while in AP mode"""
    try:
        networks = await ap_manager.scan_networks()
        return networks
    except Exception as e:
        logger.error(f"Error scanning networks in AP mode: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/connect")
async def connect_from_ap(request: WiFiConnectionRequest):
    """Connect to WiFi network from AP mode"""
    try:
        await ap_manager.connect_and_switch_to_client(request.ssid, request.password)
        return {
            "status": "success",
            "message": f"Connected to {request.ssid} and switched to client mode",
            "ssid": request.ssid
        }
    except ConnectionError as e:
        # Map error types to appropriate HTTP status codes
        error_codes = {
            "auth_error": 401,      # Unauthorized (wrong password)
            "network_error": 404,   # Not Found (network not found)
            "mode_error": 400,      # Bad Request (wrong mode)
            "connection_error": 503, # Service Unavailable (connection failed)
            "unknown_error": 500     # Internal Server Error
        }
        status_code = error_codes.get(e.error_type, 500)
        raise HTTPException(status_code=status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Unexpected error in connect_from_ap: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_ap_status():
    """Get current AP mode status including available networks"""
    try:
        status = await ap_manager.get_ap_status()
        return status
    except Exception as e:
        logger.error(f"Error getting AP status: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 