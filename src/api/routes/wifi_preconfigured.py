from fastapi import APIRouter, HTTPException
from src.core.wifi_manager import WiFiManager
import logging

router = APIRouter(prefix="/wifi")
wifi_manager = WiFiManager()
logger = logging.getLogger(__name__)

@router.post("/connect/preconfigured", tags=["WiFi"])
async def connect_to_preconfigured():
    """Connect to the preconfigured network directly"""
    try:
        logger.debug("Attempting to connect to preconfigured network")
        result = wifi_manager._run_command([
            'sudo', 'nmcli', 'connection', 'up', 'preconfigured'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            logger.error(f"Failed to connect to preconfigured network: {result.stderr}")
            raise HTTPException(status_code=400, detail="Failed to connect to preconfigured network")
            
        verify_result = wifi_manager._run_command([
            'sudo', 'nmcli', '-t', '-f', 'GENERAL.STATE', 'device', 'show', 'wlan0'
        ], capture_output=True, text=True)
        
        if verify_result.returncode == 0 and '100 (connected)' in verify_result.stdout:
            return {"message": "Successfully connected to preconfigured network"}
        
        raise HTTPException(status_code=400, detail="Failed to verify connection")
        
    except Exception as e:
        logger.error(f"Error connecting to preconfigured network: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e)) 