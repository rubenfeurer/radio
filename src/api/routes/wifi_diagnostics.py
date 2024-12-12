from fastapi import APIRouter, HTTPException
from src.core.wifi_manager import WiFiManager
import logging

router = APIRouter(prefix="/wifi")
wifi_manager = WiFiManager()
logger = logging.getLogger(__name__)

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

@router.get("/debug_nmcli", tags=["Diagnostics"])
async def debug_nmcli():
    """Debug endpoint to execute nmcli commands and return raw output"""
    try:
        list_result = wifi_manager._run_command([
            'sudo', 'nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY,IN-USE',
            'device', 'wifi', 'list'
        ], capture_output=True, text=True, timeout=5)
        
        saved_result = wifi_manager._run_command([
            'sudo', 'nmcli', '-t', '-f', 'NAME,TYPE,FILENAME', 'connection', 'show'
        ], capture_output=True, text=True)
        
        return {
            "available_networks_output": list_result.stdout,
            "saved_connections_output": saved_result.stdout,
            "list_error": list_result.stderr,
            "saved_error": saved_result.stderr
        }
    except Exception as e:
        logger.error(f"Error executing nmcli commands: {e}")
        return {"error": str(e)} 