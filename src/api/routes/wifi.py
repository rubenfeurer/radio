import logging

from fastapi import APIRouter, HTTPException

from src.api.models.requests import WiFiConnectionRequest
from src.core.models import WiFiStatus
from src.core.wifi_manager import WiFiManager

router = APIRouter(prefix="/wifi")
wifi_manager = WiFiManager()
logger = logging.getLogger(__name__)


@router.get("/status", response_model=WiFiStatus, tags=["WiFi"])
async def get_wifi_status():
    """Get current WiFi status including connection state and available networks"""
    try:
        status = wifi_manager.get_current_status()
        status.preconfigured_ssid = wifi_manager.get_preconfigured_ssid()
        return status
    except Exception as e:
        logger.error(f"Error in get_wifi_status: {e}")
        return WiFiStatus(
            ssid=None,
            signal_strength=None,
            is_connected=False,
            has_internet=False,
            available_networks=[],
            preconfigured_ssid=None,
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
        error_msg = str(e)
        if "invalid password" in error_msg.lower():
            error_msg = "Invalid password"
        logger.error(f"Error connecting to network: {error_msg}")
        raise HTTPException(status_code=400, detail=error_msg)


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
                "has_internet": status.has_internet,
            }
        return {"ssid": None, "is_connected": False}
    except Exception as e:
        logger.error(f"Error getting current connection: {e}")
        return {"ssid": None, "is_connected": False}


@router.get("/debug", tags=["Diagnostics"])
async def debug_wifi():
    """Debug endpoint to check WiFi status with detailed logging"""
    wifi = WiFiManager()
    wifi.logger.setLevel(logging.DEBUG)
    if not wifi.logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("DEBUG: %(message)s"))
        wifi.logger.addHandler(handler)

    status = wifi.get_current_status()
    return status


@router.get("/debug_nmcli", tags=["Diagnostics"])
async def debug_nmcli():
    """Debug endpoint to execute nmcli commands and return raw output"""
    try:
        # Execute the nmcli command to list available networks
        list_result = wifi_manager._run_command(
            [
                "sudo",
                "nmcli",
                "-t",
                "-f",
                "SSID,SIGNAL,SECURITY,IN-USE",
                "device",
                "wifi",
                "list",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        # Execute the nmcli command to show saved connections
        saved_result = wifi_manager._run_command(
            ["sudo", "nmcli", "-t", "-f", "NAME,TYPE,FILENAME", "connection", "show"],
            capture_output=True,
            text=True,
        )

        return {
            "available_networks_output": list_result.stdout,
            "saved_connections_output": saved_result.stdout,
            "list_error": list_result.stderr,
            "saved_error": saved_result.stderr,
        }
    except Exception as e:
        logger.error(f"Error executing nmcli commands: {e}")
        return {"error": str(e)}


@router.post("/connect/preconfigured", tags=["WiFi"])
async def connect_to_preconfigured():
    """Connect to the preconfigured network directly"""
    try:
        logger.debug("Attempting to connect to preconfigured network")
        result = wifi_manager._run_command(
            ["sudo", "nmcli", "connection", "up", "preconfigured"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            logger.error(f"Failed to connect to preconfigured network: {result.stderr}")
            raise HTTPException(
                status_code=400,
                detail="Failed to connect to preconfigured network",
            )

        # Verify connection was successful
        verify_result = wifi_manager._run_command(
            ["sudo", "nmcli", "-t", "-f", "GENERAL.STATE", "device", "show", "wlan0"],
            capture_output=True,
            text=True,
        )

        if verify_result.returncode == 0 and "100 (connected)" in verify_result.stdout:
            return {"message": "Successfully connected to preconfigured network"}

        raise HTTPException(status_code=400, detail="Failed to verify connection")

    except Exception as e:
        logger.error(f"Error connecting to preconfigured network: {e!s}")
        raise HTTPException(status_code=400, detail=str(e))


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
        logger.error(f"Error removing network: {e!s}")
        raise HTTPException(status_code=400, detail=str(e))
