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
    try:
        # Get WiFi status
        wifi_status = await wifi_manager.get_current_status()
        wifi_status.preconfigured_ssid = await wifi_manager.get_preconfigured_ssid()

        # Get mode status
        current_mode = await mode_manager.detect_current_mode()
        mode_status = ModeStatus(
            mode=current_mode.value,
            is_switching=mode_manager.is_switching,
            is_temp_mode=mode_manager.is_temp_mode
        )

        # Combine into NetworkStatus
        return NetworkStatus(
            wifi_status=wifi_status,
            mode_status=mode_status
        )
    except Exception as e:
        logger.error(f"Error in get_network_status: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Internal Server Error. Check server logs for details."
        )

@router.get("/mode", tags=["Mode"])
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

@router.post("/mode/{mode}", tags=["Mode"])
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

@router.post("/scan", tags=["AP"])
async def trigger_network_scan():
    """Trigger a network scan in either AP or CLIENT mode"""
    try:
        current_mode = await mode_manager.detect_current_mode()
        logger.debug(f"Scanning networks in {current_mode} mode")

        if current_mode == NetworkMode.CLIENT:
            # In CLIENT mode, use WiFiManager's existing scan functionality
            status = await wifi_manager.get_current_status()
            return {"status": "success", "networks": status.available_networks}
        else:
            # In AP mode, use iw scan
            try:
                scan_cmd = await wifi_manager._run_command([
                    'sudo', 'iw', 'dev', 'wlan0', 'scan'
                ], capture_output=True, text=True, timeout=10)
                
                if scan_cmd.returncode != 0:
                    logger.error(f"iw scan failed: {scan_cmd.stderr}")
                    raise HTTPException(status_code=500, detail="Network scan failed")

                # Parse scan results
                networks = []
                current_network = None
                
                for line in scan_cmd.stdout.split('\n'):
                    line = line.strip()
                    
                    if line.startswith('BSS '):
                        if current_network and current_network.get('ssid'):
                            networks.append(WiFiNetwork.from_iw_scan(
                                ssid=current_network['ssid'],
                                signal_dbm=current_network.get('signal', -100),
                                security=current_network.get('security')
                            ))
                        current_network = {}
                    
                    elif line.startswith('signal:'):
                        try:
                            signal_dbm = float(line.split()[1])
                            current_network['signal'] = signal_dbm
                        except (IndexError, ValueError):
                            pass
                    
                    elif line.startswith('SSID:'):
                        try:
                            ssid = line.split('SSID:', 1)[1].strip()
                            if ssid and not ssid.isspace():
                                current_network['ssid'] = ssid
                        except IndexError:
                            pass
                    
                    elif any(sec in line for sec in ['WPA', 'WEP']):
                        current_network['security'] = 'WPA2'

                # Add the last network if exists
                if current_network and current_network.get('ssid'):
                    networks.append(WiFiNetwork.from_iw_scan(
                        ssid=current_network['ssid'],
                        signal_dbm=current_network.get('signal', -100),
                        security=current_network.get('security')
                    ))

                # Remove duplicates and sort by signal strength
                unique_networks = {}
                for network in networks:
                    if network.ssid not in unique_networks or \
                       network.signal_strength > unique_networks[network.ssid].signal_strength:
                        unique_networks[network.ssid] = network

                sorted_networks = sorted(
                    unique_networks.values(),
                    key=lambda x: x.signal_strength,
                    reverse=True
                )

                return {"status": "success", "networks": sorted_networks}
                
            except Exception as e:
                logger.error(f"Error during iw scan: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error during network scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint for real-time updates
@router.websocket("/ws/mode")
async def mode_status_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time mode status updates"""
    await websocket.accept()
    
    try:
        while True:
            try:
                # Get current mode status
                current_mode = mode_manager.current_mode if mode_manager.is_temp_mode else await mode_manager.detect_current_mode()
                
                # Prepare status data
                status_data = {
                    "type": "mode_status",
                    "data": {
                        "mode": current_mode.value,
                        "is_switching": mode_manager.is_switching,
                        "is_temp_mode": mode_manager.is_temp_mode
                    }
                }
                
                # Send status update
                await websocket.send_json(status_data)
                
                # Wait for a short period before next update
                await asyncio.sleep(1)
                
                # Optional: Check if client is still connected
                try:
                    # Use receive_text with a timeout to check connection
                    await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                except asyncio.TimeoutError:
                    # This is expected, continue normal operation
                    continue
                except WebSocketDisconnect:
                    logger.debug("Client disconnected")
                    break
                
            except WebSocketDisconnect:
                logger.debug("WebSocket disconnected")
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                try:
                    await websocket.send_json({"error": str(e)})
                except:
                    pass
                break
                
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
    finally:
        try:
            await websocket.close()
        except:
            pass 

@router.post("/ap/connect", tags=["AP"])
async def connect_from_ap_mode(request: WiFiConnectionRequest):
    """Connect to a WiFi network from AP mode"""
    try:
        logger.debug(f"Attempting to connect to network: {request.ssid}")
        
        # First attempt to switch to client mode temporarily
        success = await mode_manager.temp_switch_to_client_mode()
        if not success:
            raise HTTPException(status_code=400, detail="Failed to switch to client mode")
        
        try:
            # Attempt connection
            result = await wifi_manager.connect_to_network(request.ssid, request.password)
            
            if result:
                # If connection successful, stay in client mode
                logger.debug("Connection successful, staying in client mode")
                return {"status": "success"}
            else:
                # If connection failed, revert to AP mode
                logger.debug("Connection failed, reverting to AP mode")
                await mode_manager.restore_previous_mode()
                raise HTTPException(status_code=400, detail="Failed to connect to network")
                
        except Exception as e:
            # On any error, ensure we revert to AP mode
            logger.error(f"Error during connection attempt: {e}")
            await mode_manager.restore_previous_mode()
            raise HTTPException(status_code=400, detail=str(e))
            
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error in connect_from_ap_mode: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 