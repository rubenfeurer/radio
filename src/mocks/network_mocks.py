import logging
import subprocess
from typing import Any, Dict

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
                "in_use": True,
            },
            "Mock WiFi 2": {
                "signal": 75,
                "security": "WPA2",
                "saved": False,
                "in_use": False,
            },
        }
        self._connected_ssid = "Mock WiFi 1"

    def _run_command(
        self, command: list[str], **kwargs
    ) -> subprocess.CompletedProcess[str]:
        """Mock command execution with proper return type"""
        logger.debug(f"Mock executing: {' '.join(command)}")
        return subprocess.CompletedProcess(
            args=command, returncode=0, stdout="mock output", stderr=""
        )

    def some_function(self) -> bool:
        """Mock function with explicit return"""
        return True

    def get_network_status(self) -> Dict[str, Any]:
        """Get mock network status"""
        return {"connected": True, "ssid": "Test Network", "signal_strength": 100}
