from fastapi import APIRouter, HTTPException
import logging
from src.core.mode_manager import ModeManagerSingleton, NetworkMode
from src.core.wifi_manager import WiFiManager

router = APIRouter(prefix="/mode", tags=["Mode"])
mode_manager = ModeManagerSingleton.get_instance()
wifi_manager = WiFiManager()
logger = logging.getLogger(__name__)

@router.get("/current")
async def get_current_mode():
    """Get current network mode (AP/Client)"""
    try:
        current_mode = mode_manager.detect_current_mode()
        return {
            "mode": current_mode,
            "ap_ssid": mode_manager.AP_SSID if current_mode == NetworkMode.AP else None,
            "is_connected": wifi_manager.get_current_status().is_connected if current_mode == NetworkMode.CLIENT else True
        }
    except Exception as e:
        logger.error(f"Error getting current mode: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ap")
async def enable_ap_mode():
    """Switch to Access Point mode"""
    try:
        if await mode_manager.enable_ap_mode():
            return {
                "status": "success",
                "mode": NetworkMode.AP,
                "ap_ssid": mode_manager.AP_SSID
            }
        raise HTTPException(status_code=500, detail="Failed to enable AP mode")
    except Exception as e:
        logger.error(f"Error enabling AP mode: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/client")
async def enable_client_mode():
    """Switch to Client mode"""
    try:
        if await mode_manager.enable_client_mode():
            return {
                "status": "success",
                "mode": NetworkMode.CLIENT
            }
        raise HTTPException(status_code=500, detail="Failed to enable client mode")
    except Exception as e:
        logger.error(f"Error enabling client mode: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scan")
async def scan_networks_in_ap_mode():
    """Temporarily switch to client mode, scan networks, and restore AP mode"""
    try:
        current_mode = mode_manager.detect_current_mode()
        if current_mode != NetworkMode.AP:
            raise HTTPException(status_code=400, detail="Device must be in AP mode to use this endpoint")

        # Perform scan (this will temporarily disable AP)
        networks = await mode_manager.scan_networks_in_ap_mode()
        
        return {
            "status": "success",
            "networks": networks
        }
    except Exception as e:
        logger.error(f"Error scanning networks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/toggle")
async def toggle_network_mode():
    """Toggle between AP and Client modes"""
    try:
        current_mode = mode_manager.detect_current_mode()
        new_mode = await mode_manager.toggle_mode()
        
        response = {
            "status": "success",
            "previous_mode": current_mode,
            "current_mode": new_mode,
        }
        
        # Add AP SSID if in AP mode
        if new_mode == NetworkMode.AP:
            response["ap_ssid"] = mode_manager.AP_SSID
            
        return response
        
    except Exception as e:
        logger.error(f"Error toggling network mode: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 