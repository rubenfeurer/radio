from fastapi import APIRouter, HTTPException
from src.core.wifi_manager import WiFiManager
from src.core.models import NetworkMode, NetworkModeStatus
from config.config import settings
import subprocess
import logging

# Use the existing WiFiManager instance from wifi.py
from .wifi import wifi_manager

logger = logging.getLogger(__name__)

# Create endpoint function without router
async def get_network_mode():
    """Get current network mode (AP or client mode)"""
    try:
        mode = wifi_manager.get_operation_mode()
        logger.debug(f"Current network mode: {mode}")
        return mode
    except Exception as e:
        logger.error(f"Error getting network mode: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get network mode: {str(e)}"
        )

async def toggle_ap_mode():
    """Toggle between AP and client mode"""
    try:
        current_mode = wifi_manager.get_operation_mode()
        logger.info(f"Current mode before toggle: {current_mode}")
        
        if current_mode.mode == NetworkMode.AP:
            logger.info("Disabling AP mode...")
            result = wifi_manager.disable_ap_mode()
            if not result:
                logger.error("Failed to disable AP mode")
                raise HTTPException(status_code=500, detail="Failed to disable AP mode")
            logger.info("AP mode disabled successfully")
        else:
            logger.info("Enabling AP mode...")
            result = wifi_manager.enable_ap_mode(
                ssid=settings.HOSTNAME,
                password=settings.AP_PASSWORD,
                channel=settings.AP_CHANNEL,
                ip=settings.AP_IP
            )
            if not result:
                logger.error("Failed to enable AP mode")
                raise HTTPException(status_code=500, detail="Failed to enable AP mode")
            logger.info("AP mode enabled successfully")
        
        # Get new mode after toggle
        new_mode = wifi_manager.get_operation_mode()
        logger.info(f"New mode after toggle: {new_mode}")
        return new_mode
        
    except Exception as e:
        logger.error(f"Failed to toggle AP mode: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to toggle AP mode: {str(e)}"
        )

# Add the endpoints to the existing wifi router
from .wifi import router
router.add_api_route("/mode", get_network_mode, response_model=NetworkModeStatus, methods=["GET"])
router.add_api_route("/mode/toggle", toggle_ap_mode, response_model=NetworkModeStatus, methods=["POST"]) 