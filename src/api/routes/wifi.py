from fastapi import APIRouter, HTTPException, Query, WebSocket, Depends
from typing import List
from src.core.wifi_manager import WiFiManager
from src.core.models import WiFiStatus, WiFiNetwork
from src.api.models.requests import WiFiConnectionRequest
from src.core.mode_manager import mode_manager, NetworkMode
from src.core.models import NetworkStatus, ModeStatus
from src.utils.logger import logger
import logging
import asyncio
from starlette.websockets import WebSocketDisconnect

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

@router.get("/mode")
async def get_mode():
    """Get current network mode"""
    try:
        logger.debug("Mode request received")
        current_mode = await mode_manager.detect_current_mode()
        logger.debug(f"Mode detection result: {current_mode}")
        return {
            "mode": current_mode.value,
            "is_switching": mode_manager.is_switching
        }
    except Exception as e:
        logger.error(f"Error in get_mode endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/mode/{mode}")
async def switch_mode(mode: str):
    """Switch between AP and CLIENT modes"""
    try:
        logger.debug(f"Switching to mode: {mode}")
        # Make case-insensitive by converting to uppercase
        new_mode = NetworkMode[mode.upper()]
        result = await mode_manager.switch_mode(new_mode)
        logger.debug(f"Switch result: {result}")
        return {"success": result}
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Invalid mode: {mode}")
    except Exception as e:
        logger.error(f"Error switching mode: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scan", tags=["WiFi"])
async def trigger_network_scan():
    """Trigger a network scan from AP mode"""
    try:
        current_mode = await mode_manager.detect_current_mode()
        if current_mode != NetworkMode.AP:
            raise HTTPException(
                status_code=400,
                detail="Can only scan from AP mode"
            )

        results = await mode_manager.scan_from_ap_mode()
        if results is None:
            raise HTTPException(status_code=500, detail="Scan failed")

        return {"status": "success", "networks": results}
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error during network scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/scan-results", tags=["WiFi"])
async def get_scan_results():
    """Get the latest scan results"""
    try:
        if not hasattr(mode_manager, '_scan_results'):
            return {"networks": []}
        return {"networks": mode_manager._scan_results or []}
    except Exception as e:
        logger.error(f"Error getting scan results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint for real-time updates
@router.websocket("/ws/mode")
async def mode_status_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            try:
                if not mode_manager.is_temp_mode:
                    mode = await mode_manager.detect_current_mode()
                else:
                    mode = mode_manager.current_mode
                    logger.debug(f"In temporary mode, using current mode: {mode}")

                await websocket.send_json({
                    "type": "mode_status",
                    "data": {
                        "mode": mode.value,
                        "is_switching": mode_manager.is_switching,
                        "is_temp_mode": mode_manager.is_temp_mode,
                        "scan_in_progress": mode_manager.is_switching and mode_manager.is_temp_mode
                    }
                })
                
                # Wait for client message or disconnect
                try:
                    await websocket.receive_text()
                except WebSocketDisconnect:
                    logger.debug("WebSocket client disconnected during receive")
                    return
                
                await asyncio.sleep(1)
            except WebSocketDisconnect:
                logger.debug("WebSocket client disconnected")
                return
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                try:
                    await websocket.send_json({"error": str(e)})
                except:
                    pass
                return
    finally:
        try:
            await websocket.close()
        except:
            pass 