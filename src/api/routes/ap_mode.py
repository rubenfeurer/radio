from fastapi import APIRouter, HTTPException
from src.core.wifi_manager import WiFiManager
from src.core.models import NetworkMode, NetworkModeStatus, WiFiNetwork, WiFiStatus
from config.config import settings
import logging
import subprocess
from typing import List

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/wifi")
wifi_manager = WiFiManager()

@router.get("/mode", response_model=NetworkModeStatus)
async def get_network_mode():
    """Get current network mode (AP or normal)"""
    try:
        return wifi_manager.get_operation_mode()
    except Exception as e:
        logger.error(f"Error getting network mode: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get network mode: {str(e)}"
        )

@router.get("/ap/networks", response_model=List[WiFiNetwork])
async def scan_networks_in_ap_mode():
    """Scan for available networks while in AP mode"""
    try:
        # Use iw to scan without disrupting AP mode
        result = subprocess.run(
            ['sudo', 'iw', 'dev', 'wlan0', 'scan'],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            logger.error(f"Scan failed: {result.stderr}")
            raise HTTPException(status_code=500, detail="Network scan failed")
            
        networks = []
        current_network = {}
        
        for line in result.stdout.split('\n'):
            line = line.strip()
            if 'BSS' in line:
                if current_network and current_network.get('ssid'):
                    networks.append(WiFiNetwork(
                        ssid=current_network['ssid'],
                        signal_strength=current_network.get('signal', 0),
                        security=current_network.get('security'),
                        in_use=False
                    ))
                current_network = {}
            elif 'SSID:' in line:
                current_network['ssid'] = line.split('SSID:')[1].strip()
            elif 'signal:' in line:
                # Convert dBm to percentage (roughly)
                dbm = float(line.split('signal:')[1].split('dBm')[0].strip())
                signal = min(100, max(0, int((dbm + 100) * 2)))
                current_network['signal'] = signal
                
        # Add the last network if exists
        if current_network and current_network.get('ssid'):
            networks.append(WiFiNetwork(
                ssid=current_network['ssid'],
                signal_strength=current_network.get('signal', 0),
                security=current_network.get('security'),
                in_use=False
            ))
            
        return networks
        
    except Exception as e:
        logger.error(f"Error scanning networks in AP mode: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to scan networks: {str(e)}"
        )

@router.post("/mode/toggle", response_model=NetworkModeStatus)
async def toggle_ap_mode():
    """Toggle between AP mode and normal mode"""
    try:
        current_mode = wifi_manager.get_operation_mode()
        
        if current_mode.mode == NetworkMode.AP:
            # Currently in AP mode, switch to normal mode
            success = wifi_manager.disable_ap_mode()
            if not success:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to disable AP mode"
                )
            return NetworkModeStatus(
                mode=NetworkMode.DEFAULT,
                ip_address=wifi_manager.get_ip_address()
            )
        else:
            # Currently in normal mode, switch to AP mode
            success = wifi_manager.enable_ap_mode(
                ssid=settings.AP_SSID,
                password=settings.AP_PASSWORD,
                ip=settings.AP_IP
            )
            if not success:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to enable AP mode"
                )
            return NetworkModeStatus(
                mode=NetworkMode.AP,
                ap_ssid=settings.AP_SSID,
                ap_password=settings.AP_PASSWORD,
                ip_address=settings.AP_IP
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling AP mode: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.get("/ap/status", response_model=WiFiStatus)
async def get_ap_status():
    """Get current AP mode status and scan for available networks"""
    try:
        # Check if hostapd is running
        result = subprocess.run(
            ['sudo', 'systemctl', 'is-active', 'hostapd'],
            capture_output=True,
            text=True
        )
        
        is_active = result.returncode == 0
        
        if not is_active:
            return WiFiStatus(
                ssid=None,
                signal_strength=None,
                is_connected=False,
                has_internet=False,
                available_networks=[]
            )
            
        # Scan for available networks
        logger.debug("Scanning for networks in AP mode...")
        scan_result = subprocess.run(
            ['sudo', 'iwlist', 'wlan0', 'scan'],  # Using iwlist instead of iw for more reliable output
            capture_output=True,
            text=True
        )
        
        networks = []
        if scan_result.returncode == 0:
            current_network = {}
            for line in scan_result.stdout.split('\n'):
                line = line.strip()
                if 'ESSID:' in line:
                    ssid = line.split('ESSID:')[1].strip('"')
                    if ssid and ssid != settings.AP_SSID:  # Don't include our own AP
                        current_network['ssid'] = ssid
                elif 'Quality=' in line:
                    # Parse signal quality (e.g., "Quality=70/70  Signal level=-30 dBm")
                    quality = line.split('=')[1].split()[0]
                    try:
                        current_val, max_val = map(int, quality.split('/'))
                        signal_strength = int((current_val / max_val) * 100)
                        current_network['signal_strength'] = signal_strength
                    except (ValueError, ZeroDivisionError):
                        current_network['signal_strength'] = 0
                elif 'Encryption key:' in line:
                    # Set security based on encryption status (explicitly check for 'off')
                    is_encrypted = 'off' not in line.lower()
                    current_network['security'] = 'WPA2' if is_encrypted else None
                    
                    # If we have all network info, add it to the list
                    if 'ssid' in current_network:
                        networks.append(WiFiNetwork(
                            ssid=current_network['ssid'],
                            signal_strength=current_network.get('signal_strength', 0),
                            security=current_network.get('security'),
                            in_use=False
                        ))
                        current_network = {}
        
        logger.debug(f"Found {len(networks)} networks in AP mode")
        
        return WiFiStatus(
            ssid=settings.AP_SSID,
            signal_strength=100,
            is_connected=True,
            has_internet=False,
            available_networks=networks
        )
        
    except Exception as e:
        logger.error(f"Error getting AP status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get AP status: {str(e)}"
        ) 