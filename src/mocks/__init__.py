from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class MockNetworkManager:
    def __init__(self):
        self._wifi_status = {"connected": True, "ssid": "Mock-Network"}

    async def scan_networks(self) -> list:
        return [
            {"ssid": "Mock-Network-1", "signal": 90},
            {"ssid": "Mock-Network-2", "signal": 70},
        ]

    async def connect(self, ssid: str, password: str) -> bool:
        logger.info(f"Mock connecting to network: {ssid}")
        return True


class MockGPIOController:
    def __init__(self):
        self._button_states = {1: False, 2: False, 3: False}
        self._volume = 50

    def set_button_callback(self, pin: int, callback):
        logger.info(f"Mock button callback set for pin {pin}")

    def set_volume(self, value: int):
        self._volume = max(0, min(100, value))
        logger.info(f"Mock volume set to {self._volume}")


class MockAudioPlayer:
    def __init__(self):
        self._playing = False
        self._current_url = None

    async def play(self, url: str):
        self._playing = True
        self._current_url = url
        logger.info(f"Mock playing: {url}")

    async def stop(self):
        self._playing = False
        logger.info("Mock playback stopped")
