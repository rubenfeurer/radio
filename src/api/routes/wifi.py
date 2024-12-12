from fastapi import APIRouter, HTTPException, Query, WebSocket
from typing import List
from src.core.wifi_manager import WiFiManager
from src.core.models import WiFiStatus, WiFiNetwork
from src.api.models.requests import WiFiConnectionRequest
from src.core.mode_manager import mode_manager, NetworkMode
from src.core.models import NetworkStatus, ModeStatus
import logging
import asyncio

router = APIRouter(prefix="/wifi")
wifi_manager = WiFiManager(skip_verify=True)
logger = logging.getLogger(__name__)

@router.get("/networks", response_model=List[WiFiNetwork], tags=["WiFi"])
async def get_networks():
    """Get list of available WiFi networks"""
    try:
        status = await wifi_manager.get_current_status()
        return status.available_networks
    except Exception as e:
        logger.error(f"Error getting networks: {e}")
        return []

@router.get("/status", response_model=WiFiStatus, tags=["WiFi"])
async def get_wifi_status():
    """Get current WiFi status including connection state and available networks"""
    try:
        status = await wifi_manager.get_current_status()
        status.preconfigured_ssid = await wifi_manager.get_preconfigured_ssid()
        return status
    except Exception as e:
        logger.error(f"Error in get_wifi_status: {e}")
        return WiFiStatus(
            ssid=None,
            signal_strength=None,
            is_connected=False,
            has_internet=False,
            available_networks=[],
            preconfigured_ssid=None
        )

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
        status = await wifi_manager.get_current_status()
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
    
    status = await wifi.get_current_status()
    return status 

@router.get("/debug_nmcli", tags=["Diagnostics"])
async def debug_nmcli():
    """Debug endpoint to execute nmcli commands and return raw output"""
    try:
        # Execute the nmcli command to list available networks
        list_result = await wifi_manager._run_command([
            'sudo', 'nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY,IN-USE',
            'device', 'wifi', 'list'
        ], capture_output=True, text=True, timeout=5)
        
        # Execute the nmcli command to show saved connections
        saved_result = await wifi_manager._run_command([
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

@router.post("/connect/preconfigured", tags=["WiFi"])
async def connect_to_preconfigured():
    """Connect to the preconfigured network directly"""
    try:
        logger.debug("Attempting to connect to preconfigured network")
        result = await wifi_manager._run_command([
            'sudo', 'nmcli', 'connection', 'up', 'preconfigured'
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            logger.error(f"Failed to connect to preconfigured network: {result.stderr}")
            raise HTTPException(status_code=400, detail="Failed to connect to preconfigured network")
            
        # Verify connection was successful
        verify_result = await wifi_manager._run_command([
            'sudo', 'nmcli', '-t', '-f', 'GENERAL.STATE', 'device', 'show', 'wlan0'
        ], capture_output=True, text=True)
        
        if verify_result.returncode == 0 and '100 (connected)' in verify_result.stdout:
            return {"message": "Successfully connected to preconfigured network"}
        
        raise HTTPException(status_code=400, detail="Failed to verify connection")
        
    except Exception as e:
        logger.error(f"Error connecting to preconfigured network: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e)) 

@router.delete("/forget/{ssid}", tags=["WiFi"])
async def forget_network(ssid: str):
    """Remove a saved network"""
    try:
        logger.debug(f"Attempting to forget network: {ssid}")
        result = await wifi_manager._remove_connection(ssid)
        if result:
            return {"status": "success"}
        raise HTTPException(status_code=400, detail="Failed to remove network")
    except Exception as e:
        logger.error(f"Error removing network: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e)) 

@router.get("/network_status", response_model=NetworkStatus, tags=["WiFi"])
async def get_network_status():
    """Get combined WiFi and mode status including connection and mode information"""
    wifi_status = await get_wifi_status()
    mode = await mode_manager.detect_current_mode()
    mode_status = ModeStatus(
        mode=mode.value,
        is_switching=mode_manager.is_switching
    )
    return NetworkStatus(
        wifi_status=wifi_status,
        mode_status=mode_status
    )

@router.get("/mode", response_model=ModeStatus, tags=["WiFi"])
async def get_current_mode():
    """Get current network mode (AP/Client)"""
    mode = await mode_manager.detect_current_mode()
    return ModeStatus(
        mode=mode.value,
        is_switching=mode_manager.is_switching
    )

@router.post("/mode/{mode}", tags=["WiFi"])
async def switch_mode(mode: str):
    """Switch between AP and Client mode"""
    try:
        target_mode = NetworkMode(mode.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid mode. Use 'ap' or 'client'")
    
    if mode_manager.is_switching:
        raise HTTPException(status_code=409, detail="Mode switch already in progress")
    
    success = await mode_manager.switch_mode(target_mode)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to switch mode")
    
    return {"message": f"Successfully switched to {mode} mode"}

# WebSocket endpoint for real-time updates
@router.websocket("/ws/mode")
async def mode_status_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Send current mode status every second
            mode = await mode_manager.detect_current_mode()
            await websocket.send_json({
                "type": "mode_status",
                "data": {
                    "mode": mode.value,
                    "is_switching": mode_manager.is_switching
                }
            })
            await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close() 