from fastapi import APIRouter, HTTPException
from src.core.wifi_manager import WiFiManager
from src.core.models import NetworkMode, NetworkModeStatus

# Use the existing WiFiManager instance from wifi.py
from .wifi import wifi_manager

# Create endpoint function without router
async def get_network_mode():
    """Get current network mode (AP or client mode)"""
    try:
        return NetworkModeStatus(
            mode=NetworkMode.DEFAULT,  # Temporary default until we implement get_operation_mode
            ip_address=None
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get network mode: {str(e)}"
        )

# Add the endpoint to the existing wifi router
from .wifi import router
router.add_api_route("/mode", get_network_mode, response_model=NetworkModeStatus, methods=["GET"]) 