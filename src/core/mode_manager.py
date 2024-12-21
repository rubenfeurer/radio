from enum import Enum
import subprocess
import logging
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from config.config import settings
import os
import asyncio
from datetime import datetime

# Set up logger
logger = logging.getLogger(__name__)

class NetworkMode(Enum):
    AP = "AP"
    CLIENT = "CLIENT"

class ModeManagerSingleton:
    _instance = None

    def __init__(self):
        if ModeManagerSingleton._instance is not None:
            raise Exception("Use get_instance() instead")
        self.logger = logging.getLogger(__name__)
        self.AP_SSID = settings.HOSTNAME
        self.AP_PASS = settings.AP_PASSWORD
        self._MODE_FILE = Path('/tmp/radio/radio_mode.json')
        self._current_mode = None
        self._load_state()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _save_state(self, mode: NetworkMode):
        """Save current mode to state file"""
        try:
            self._MODE_FILE.parent.mkdir(parents=True, exist_ok=True)
            self._MODE_FILE.write_text(json.dumps({"mode": mode.value}))
            logger.debug(f"Saved mode state: {mode.value}")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def _load_state(self) -> Optional[NetworkMode]:
        """Load mode from state file"""
        try:
            if self._MODE_FILE.exists():
                data = json.loads(self._MODE_FILE.read_text())
                mode = NetworkMode(data["mode"])
                logger.debug(f"Loaded mode state: {mode.value}")
                return mode
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
        return None

    def detect_current_mode(self) -> NetworkMode:
        """Detect current network mode based on actual network configuration."""
        try:
            logger.debug("Starting mode detection...")
            
            # Check if running as AP/Hotspot
            result = subprocess.run(['nmcli', 'device', 'show', 'wlan0'], 
                                  capture_output=True, text=True)
            
            logger.debug(f"Network status from nmcli: {result.stdout}")
            
            if 'AP' in result.stdout or 'Hotspot' in result.stdout:
                logger.info("Detected AP/Hotspot mode from network status")
                return NetworkMode.AP
            
            logger.info("Detected client mode from network status")
            return NetworkMode.CLIENT
                
        except Exception as e:
            logger.error(f"Error detecting mode: {str(e)}", exc_info=True)
            return NetworkMode.AP  # Default to AP mode

    def _verify_mode(self, mode: NetworkMode) -> bool:
        """Verify that saved mode matches actual mode"""
        try:
            if mode == NetworkMode.AP:
                result = subprocess.run(
                    ['nmcli', '-t', '-f', 'MODE', 'device', 'wifi', 'list', 'ifname', 'wlan0'],
                    capture_output=True, text=True
                )
                return 'AP' in result.stdout
            else:
                result = subprocess.run(
                    ['nmcli', '-t', '-f', 'GENERAL.STATE', 'device', 'show', 'wlan0'],
                    capture_output=True, text=True
                )
                return 'AP' not in result.stdout
        except Exception as e:
            self.logger.error(f"Mode verification failed: {e}")
            return False

    async def enable_ap_mode(self) -> None:
        try:
            logger.info(f"Enabling AP mode with SSID: {self.AP_SSID}, Password: {self.AP_PASS}")
            
            # Save current WiFi status before switching
            try:
                from .wifi_manager import WiFiManager
                wifi_manager = WiFiManager()
                
                # Get comprehensive WiFi status
                status = wifi_manager.get_current_status()
                
                data_dir = Path("data")
                data_dir.mkdir(exist_ok=True)
                
                # Create a more detailed status dictionary
                wifi_status = {
                    "ssid": status.ssid,
                    "signal_strength": status.signal_strength,
                    "is_connected": status.is_connected,
                    "has_internet": status.has_internet,
                    "available_networks": [
                        {
                            "ssid": net.ssid,
                            "signal_strength": net.signal_strength,
                            "security": net.security,
                            "in_use": net.in_use,
                            "saved": net.saved
                        } for net in status.available_networks
                    ],
                    "timestamp": str(datetime.now())
                }
                
                # Save to JSON file
                status_file = data_dir / "last_wifi_status.json"
                logger.info(f"Saving detailed WiFi status to {status_file}")
                with open(status_file, 'w') as f:
                    json.dump(wifi_status, f, indent=2)
                
            except Exception as e:
                logger.error(f"Failed to save WiFi status: {e}")
                # Continue with mode switch even if save fails
            
            # First disconnect from current network
            disconnect_result = subprocess.run(
                ['sudo', 'nmcli', 'device', 'disconnect', 'wlan0'],
                capture_output=True,
                text=True
            )
            logger.debug(f"Disconnect result: {disconnect_result.stdout} {disconnect_result.stderr}")
            
            await asyncio.sleep(2)
            
            # Remove existing hotspot connection
            delete_result = subprocess.run(
                ['sudo', 'nmcli', 'connection', 'delete', 'Hotspot'], 
                capture_output=True,
                text=True
            )
            logger.debug(f"Delete result: {delete_result.stdout} {delete_result.stderr}")
            
            # Create new hotspot with explicit security settings
            cmd = [
                'sudo', 'nmcli', 'connection', 'add',
                'type', 'wifi',
                'ifname', 'wlan0',
                'con-name', 'Hotspot',
                'autoconnect', 'yes',
                'ssid', self.AP_SSID,
                'mode', 'ap',
                'ipv4.method', 'shared',
                '802-11-wireless-security.key-mgmt', 'wpa-psk',
                '802-11-wireless-security.psk', self.AP_PASS,
                '802-11-wireless-security.proto', 'rsn',
                '802-11-wireless-security.pairwise', 'ccmp',
                '802-11-wireless-security.group', 'ccmp',
                '802-11-wireless.band', settings.AP_BAND,
                '802-11-wireless.channel', str(settings.AP_CHANNEL)
            ]
            logger.debug(f"Running command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                error_msg = f"Failed to create AP connection. Return code: {result.returncode}\nStdout: {result.stdout}\nStderr: {result.stderr}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            # Activate the connection
            activate_cmd = ['sudo', 'nmcli', 'connection', 'up', 'Hotspot']
            activate_result = subprocess.run(activate_cmd, capture_output=True, text=True)
            
            if activate_result.returncode != 0:
                error_msg = f"Failed to activate AP mode. Return code: {activate_result.returncode}\nStdout: {activate_result.stdout}\nStderr: {activate_result.stderr}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            logger.info("AP mode enabled successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error enabling AP mode: {str(e)}", exc_info=True)
            raise

    async def enable_client_mode(self) -> None:
        """Enable client mode and connect to last known network if available"""
        try:
            logger.info("Enabling client mode...")
            
            # Set device to managed mode
            subprocess.run(['sudo', 'nmcli', 'device', 'set', 'wlan0', 'managed'], 
                          capture_output=True)
            
            # Get list of saved connections
            result = subprocess.run(['sudo', 'nmcli', 'connection', 'show'], 
                                  capture_output=True, text=True)
            
            if 'preconfigured' in result.stdout:
                logger.info("Connecting to preconfigured network...")
                subprocess.run(['sudo', 'nmcli', 'connection', 'up', 'preconfigured'], 
                             capture_output=True)
            
            # Wait for connection
            max_attempts = 15
            for attempt in range(max_attempts):
                check = subprocess.run(['nmcli', 'networking', 'connectivity', 'check'],
                                     capture_output=True, text=True)
                if 'full' in check.stdout:
                    logger.info("Network connection established")
                    break
                await asyncio.sleep(1)
                
            self._save_state(NetworkMode.CLIENT)
            logger.info("Client mode enabled successfully")
            
        except Exception as e:
            logger.error(f"Error enabling client mode: {e}")
            raise

    async def toggle_mode(self) -> NetworkMode:
        """Toggle between AP and Client modes"""
        try:
            current_mode = self.detect_current_mode()
            
            # Switch to opposite mode
            if current_mode == NetworkMode.CLIENT:
                success = await self.enable_ap_mode()
                new_mode = NetworkMode.AP
            else:
                success = await self.enable_client_mode()
                new_mode = NetworkMode.CLIENT
                
            if success:
                self._save_state(new_mode)
                return new_mode
            
            raise Exception(f"Failed to switch to {new_mode} mode")
                
        except Exception as e:
            self.logger.error(f"Failed to toggle mode: {e}")
            raise

    async def scan_wifi_networks(self) -> List[Dict[str, Any]]:
        """Scan for available WiFi networks"""
        try:
            logger.info("Scanning for WiFi networks...")
            current_mode = await self.detect_current_mode()
            
            # If in AP mode, temporarily switch to client mode for scanning
            temp_switch = False
            if current_mode == NetworkMode.AP:
                logger.info("Temporarily switching to client mode for scanning")
                temp_switch = True
                # Don't disconnect yet, just prepare interface
                subprocess.run(['sudo', 'nmcli', 'device', 'set', 'wlan0', 'managed'], 
                             capture_output=True)
            
            # Perform the scan
            subprocess.run(['sudo', 'nmcli', 'device', 'wifi', 'rescan'], 
                          capture_output=True)
            await asyncio.sleep(2)  # Wait for scan to complete
            
            result = subprocess.run(['sudo', 'nmcli', 'device', 'wifi', 'list'], 
                                  capture_output=True, text=True)
            
            # If we temporarily switched modes, restore AP mode
            if temp_switch:
                logger.info("Restoring AP mode after scan")
                subprocess.run(['sudo', 'nmcli', 'device', 'set', 'wlan0', 'ap'], 
                             capture_output=True)
            
            # Parse the scan results
            networks = self._parse_network_scan(result.stdout)
            return networks
            
        except Exception as e:
            logger.error(f"Error scanning networks: {e}")
            raise

# For backwards compatibility
SimpleModeManager = ModeManagerSingleton