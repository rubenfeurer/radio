from enum import Enum
import subprocess
import logging
import json
from pathlib import Path
from typing import Optional
from config.config import settings

class NetworkMode(str, Enum):
    CLIENT = "client"
    AP = "ap"

class ModeManagerSingleton:
    _instance = None

    def __init__(self):
        if ModeManagerSingleton._instance is not None:
            raise Exception("Use get_instance() instead")
        self.logger = logging.getLogger(__name__)
        self.AP_SSID = settings.HOSTNAME
        self.AP_PASS = settings.AP_PASSWORD
        self.state_file = Path("/tmp/radio_mode.json")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _save_state(self, mode: NetworkMode):
        """Save current mode to state file"""
        try:
            self.state_file.write_text(json.dumps({"mode": mode}))
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")

    def _load_state(self) -> Optional[NetworkMode]:
        """Load mode from state file"""
        try:
            if self.state_file.exists():
                data = json.loads(self.state_file.read_text())
                return NetworkMode(data["mode"])
        except Exception as e:
            self.logger.error(f"Failed to load state: {e}")
        return None

    def detect_current_mode(self) -> NetworkMode:
        """Detect current network mode"""
        try:
            # First check saved state
            saved_mode = self._load_state()
            if saved_mode and self._verify_mode(saved_mode):
                return saved_mode
            
            # Detect actual mode
            result = subprocess.run(
                ['nmcli', '-t', '-f', 'MODE', 'device', 'wifi', 'list', 'ifname', 'wlan0'],
                capture_output=True, text=True
            )
            
            mode = NetworkMode.AP if 'AP' in result.stdout else NetworkMode.CLIENT
            # Save detected state
            self._save_state(mode)
            return mode
            
        except Exception as e:
            self.logger.error(f"Mode detection failed: {e}")
            # Default to client mode if detection fails
            return NetworkMode.CLIENT

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
        """Switch to AP mode"""
        try:
            cmd = [
                'sudo', 'nmcli', 'device', 'wifi', 'hotspot',
                'ifname', 'wlan0',
                'ssid', self.AP_SSID,
                'password', self.AP_PASS
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self._save_state(NetworkMode.AP)
                return True
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to enable AP mode: {e}")
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