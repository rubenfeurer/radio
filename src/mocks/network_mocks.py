import logging
import subprocess
from typing import Any, Dict, Optional

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
        self._ap_active = False
        self._ap_ssid = None

    async def connect_to_wifi(self, ssid: str, password: Optional[str] = None) -> bool:
        """Mock connecting to a WiFi network"""
        logger.info(f"Mock: Connecting to WiFi network {ssid}")
        self._connected_ssid = ssid
        self._ap_active = False
        return True

    async def disconnect_wifi(self) -> bool:
        """Mock disconnecting from WiFi"""
        logger.info("Mock: Disconnecting from WiFi")
        self._connected_ssid = None
        return True

    async def start_ap(self, ssid: str, password: Optional[str] = None) -> bool:
        """Mock starting access point"""
        logger.info(f"Mock: Starting AP with SSID {ssid}")
        self._ap_active = True
        self._ap_ssid = ssid
        self._connected_ssid = None
        return True

    async def stop_ap(self) -> bool:
        """Mock stopping access point"""
        logger.info("Mock: Stopping AP")
        self._ap_active = False
        self._ap_ssid = None
        return True

    async def get_wifi_status(self) -> dict:
        """Get mock WiFi status"""
        return {
            "connected": bool(self._connected_ssid),
            "current_ssid": self._connected_ssid,
            "ap_active": self._ap_active,
            "ap_ssid": self._ap_ssid,
            "signal_strength": 90 if self._connected_ssid else None,
            "has_internet": bool(self._connected_ssid)
        }

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
