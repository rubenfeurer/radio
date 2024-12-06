from fastapi import APIRouter, HTTPException
from src.core.wifi_manager import WiFiManager, WiFiStatus

router = APIRouter()
wifi_manager = WiFiManager()

@router.get("/status", response_model=WiFiStatus)
async def get_wifi_status():
    """Get current WiFi connection status"""
    try:
        return wifi_manager.get_current_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 