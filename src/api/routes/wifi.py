from fastapi import APIRouter, HTTPException
from typing import List
from src.core.wifi_manager import WiFiManager
from src.core.models import WiFiStatus, WiFiNetwork
from src.api.models.requests import WiFiConnectionRequest
import logging

router = APIRouter(prefix="/wifi")
wifi_manager = WiFiManager()
logger = logging.getLogger(__name__)

@router.get("/networks", response_model=List[WiFiNetwork], tags=["WiFi"])
async def get_networks():
    """Get list of available WiFi networks"""
    try:
        status = wifi_manager.get_current_status()
        return status.available_networks
    except Exception as e:
        logger.error(f"Error getting networks: {e}")
        return []

@router.get("/status", response_model=WiFiStatus, tags=["WiFi"])
async def get_wifi_status():
    """Get current WiFi status including connection state and available networks"""
    try:
        status = wifi_manager.get_current_status()
        status.preconfigured_ssid = wifi_manager.get_preconfigured_ssid()
        return status
    except Exception as e:
        logger.error(f"Error in get_wifi_status: {e}")
        return WiFiStatus()

@router.post("/connect", tags=["WiFi"])
async def connect_to_network(request: WiFiConnectionRequest):
    """Connect to a WiFi network"""
    try:
        logger.debug(f"Attempting to connect to SSID: {request.ssid}")
        result = await wifi_manager.connect_to_network(request.ssid, request.password)
        if result:
            return {"status": "success"}
        raise HTTPException(status_code=400, detail="Failed to connect to network")
    except Exception as e:
        logger.error(f"Error connecting to network: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/current", tags=["WiFi"])
async def get_current_connection():
    """Get details about the current WiFi connection"""
    try:
        status = wifi_manager.get_current_status()
        if status.is_connected:
            return {
                "ssid": status.ssid,
                "is_connected": True,
                "signal_strength": status.signal_strength,
                "has_internet": status.has_internet
            }
        return {"ssid": None, "is_connected": False}
    except Exception as e:
        logger.error(f"Error getting current connection: {e}")
        return {"ssid": None, "is_connected": False}

@router.delete("/forget/{ssid}", tags=["WiFi"])
async def forget_network(ssid: str):
    """Remove a saved network"""
    try:
        logger.debug(f"Attempting to forget network: {ssid}")
        result = wifi_manager._remove_connection(ssid)
        if result:
            return {"status": "success"}
        raise HTTPException(status_code=400, detail="Failed to remove network")
    except Exception as e:
        logger.error(f"Error removing network: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e)) 