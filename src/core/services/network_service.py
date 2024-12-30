import subprocess
from typing import List, Optional
import logging
from pathlib import Path
import os
from ..models import WiFiNetwork, WiFiStatus

logger = logging.getLogger(__name__)

class NetworkManagerService:
    """Real NetworkManager implementation"""
    def __init__(self):
        self._interface = "wlan0"
        self._verify_networkmanager()

    def _verify_networkmanager(self) -> None:
        result = self._run_command(['systemctl', 'is-active', 'NetworkManager'])
        if result.returncode != 0:
            raise RuntimeError("NetworkManager service is not active")

    def _run_command(self, command: List[str], **kwargs) -> subprocess.CompletedProcess:
        default_kwargs = {'capture_output': True, 'text': True, 'timeout': 5}
        kwargs = {**default_kwargs, **kwargs}
        return subprocess.run(['sudo'] + command, **kwargs)

class MockNetworkManagerService:
    """Mock NetworkManager for development"""
    def __init__(self):
        self._interface = "wlan0"
        self._mock_networks = [
            WiFiNetwork(ssid="Mock WiFi 1", signal_strength=90, security="WPA2", in_use=True, saved=True),
            WiFiNetwork(ssid="Mock WiFi 2", signal_strength=75, security="WPA2", in_use=False, saved=False),
        ]

    def _run_command(self, command: List[str], **kwargs) -> subprocess.CompletedProcess:
        """Mock command execution"""
        logger.debug(f"Mock executing: {' '.join(command)}")
        return subprocess.CompletedProcess(
            args=command,
            returncode=0,
            stdout="mock_output",
            stderr=""
        )

def get_network_service():
    """Factory function to get the appropriate network service"""
    if os.getenv('MOCK_SERVICES') == 'true':
        logger.info("Using mock network service")
        return MockNetworkManagerService()
    return NetworkManagerService() 