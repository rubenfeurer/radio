from fastapi import APIRouter, HTTPException
from typing import List
from src.core.wifi_manager import WiFiManager
from src.core.models import WiFiStatus, WiFiNetwork
from src.api.models.requests import WiFiConnectionRequest
import logging

router = APIRouter(prefix="/wifi", tags=["WiFi"])
wifi_manager = WiFiManager()
logger = logging.getLogger(__name__)

@router.get("/status", response_model=WiFiStatus, tags=["Network Status"])
async def get_wifi_status():
    """Get current WiFi status including connection state and available networks"""
    try:
        status = wifi_manager.get_current_status()
        logger.debug(f"WiFi status: {status}")
        return status
    except Exception as e:
        logger.error(f"Error in get_wifi_status: {e}")
        # Return a safe default status instead of raising an error
        return WiFiStatus(
            ssid=None,
            signal_strength=None,
            is_connected=False,
            has_internet=False,
            available_networks=[]
        )

@router.get("/networks", response_model=List[WiFiNetwork], tags=["Network Operations"])
async def scan_networks():
    """Scan for available WiFi networks"""
    try:
        status = wifi_manager.get_current_status()
        return status.available_networks
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/connect", tags=["Network Operations"])
async def connect_to_network(request: WiFiConnectionRequest):
    """Connect to a WiFi network"""
    try:
        success = await wifi_manager.connect_to_network(request.ssid, request.password)
        if success:
            return {"message": f"Successfully connected to {request.ssid}"}
        else:
            raise HTTPException(status_code=400, detail="Failed to connect to network")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/current", tags=["Network Status"])
async def get_current_connection():
    """Get details about the current WiFi connection"""
    try:
        status = wifi_manager.get_current_status()
        if status.is_connected:
            return {
                "ssid": status.ssid,
                "signal_strength": status.signal_strength,
                "has_internet": status.has_internet
            }
        else:
            return {"message": "Not connected to any network"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 