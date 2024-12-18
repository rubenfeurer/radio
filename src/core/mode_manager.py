from enum import Enum
import subprocess
import logging
import json
from pathlib import Path
from typing import Optional
from config.config import settings
import os

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

    async def enable_ap_mode(self) -> bool:
        """Enable AP mode"""
        try:
            logger.info("Starting AP mode switch...")
            cmd = [
                'sudo', 'nmcli', 'device', 'wifi', 'hotspot',
                'ifname', 'wlan0',
                'ssid', self.AP_SSID,
                'password', self.AP_PASS
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self._current_mode = NetworkMode.AP
                self._save_state(NetworkMode.AP)
                logger.info(f"AP mode enabled, saved state: {self._current_mode}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to enable AP mode: {e}")
            return False

    async def enable_client_mode(self) -> bool:
        """Switch to client mode"""
        try:
            # Stop hotspot
            cmd = ['sudo', 'nmcli', 'connection', 'down', 'Hotspot']
            result = subprocess.run(cmd, capture_output=True)
            
            if result.returncode == 0:
                self._save_state(NetworkMode.CLIENT)
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to enable client mode: {e}")
            return False

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

# For backwards compatibility
SimpleModeManager = ModeManagerSingleton