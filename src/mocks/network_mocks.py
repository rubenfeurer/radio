import subprocess
from typing import List
import logging
from ..core.models import WiFiNetwork, WiFiStatus

logger = logging.getLogger(__name__)

class MockNetworkManagerService:
    """Mock NetworkManager for development and testing"""
    def __init__(self):
        self._interface = "wlan0"
        self._mock_networks = {
            "Mock WiFi 1": {
                "signal": 90,
                "security": "WPA2",
                "saved": True,
                "in_use": True
            },
            "Mock WiFi 2": {
                "signal": 75,
                "security": "WPA2",
                "saved": False,
                "in_use": False
            }
        }
        self._connected_ssid = "Mock WiFi 1"

    def _run_command(self, command: List[str], **kwargs) -> subprocess.CompletedProcess:
        """Mock command execution"""
        logger.debug(f"Mock executing: {' '.join(command)}")
        # ... (keep existing mock command logic) 