from fastapi import APIRouter, HTTPException, Query
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
        return wifi_manager.get_current_status()
    except Exception as e:
        logger.error(f"Error in get_wifi_status: {e}")
        return WiFiStatus(
            ssid=None,
            signal_strength=None,
            is_connected=False,
            has_internet=False,
            available_networks=[]
        )

@router.post("/connect", tags=["WiFi"])
async def connect_to_network(request: WiFiConnectionRequest):
    """Connect to a WiFi network"""
    try:
        result = await wifi_manager.connect_to_network(request.ssid, request.password)
        
        # Check if result is a success response
        if isinstance(result, dict) and result.get("status") == "connected":
            return {"message": f"Successfully connected to {request.ssid}"}
        
        # If result indicates an error
        if isinstance(result, dict) and result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message", "Failed to connect"))
            
        # Handle boolean responses (legacy support)
        if isinstance(result, bool):
            if result:
                return {"message": f"Successfully connected to {request.ssid}"}
            raise HTTPException(status_code=400, detail="Failed to connect to network")
            
        raise HTTPException(status_code=400, detail="Unexpected response from WiFi manager")
        
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
        return {
            "ssid": None,
            "is_connected": False
        }
    except Exception as e:
        logger.error(f"Error getting current connection: {e}")
        return {
            "ssid": None,
            "is_connected": False
        }

@router.get("/debug", tags=["Diagnostics"])
async def debug_wifi():
    """Debug endpoint to check WiFi status with detailed logging"""
    wifi = WiFiManager()
    wifi.logger.setLevel(logging.DEBUG)
    if not wifi.logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('DEBUG: %(message)s'))
        wifi.logger.addHandler(handler)
    
    status = wifi.get_current_status()
    return status 