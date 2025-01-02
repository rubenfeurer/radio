import asyncio
from typing import Any, Callable, Dict, Optional
from unittest.mock import AsyncMock, Mock

from src.core.models import RadioStation, SystemStatus

stations: Dict[int, RadioStation] = {}
current_station: Optional[RadioStation] = None


def button_press_callback(button: int) -> None:
    """Handle button press with proper return type"""
    if button in stations:
        # ... existing code ...
        pass


def volume_change_callback(change: int) -> None:
    """Handle volume change with proper return type"""
    if isinstance(change, int):
        # ... existing code ...
        pass


def status_update_callback(status: SystemStatus) -> None:
    """Handle status update with proper return type"""
    # ... existing code ...
    pass


def get_status() -> SystemStatus:
    """Get system status with proper type handling"""
    return SystemStatus(current_station=None, volume=50, is_playing=False)


class MockAudioPlayer:
    """Mock implementation of AudioPlayer"""

    def __init__(self, status_update_callback: Optional[Callable] = None) -> None:
        self._status = SystemStatus(current_station=None, volume=70, is_playing=False)
        self._status_callback = status_update_callback
        self.volume = 70
        self._current_url: Optional[str] = None
        self.is_playing = False
        self.mpv_instance = Mock()
        self.mpv_instance.volume = self.volume

    async def play_stream(self, url: str) -> None:
        self._current_url = url
        self.is_playing = True
        if self._status_callback:
            await self._status_callback({"is_playing": True})

    async def stop_stream(self) -> None:
        self.is_playing = False
        self._current_url = None
        if self._status_callback:
            await self._status_callback({"is_playing": False})

    async def set_volume(self, volume: int) -> None:
        self.volume = max(0, min(100, volume))
        self.mpv_instance.volume = self.volume
        if self._status_callback:
            await self._status_callback({"volume": self.volume})


class MockGPIOController:
    """Mock implementation of GPIOController"""

    def __init__(
        self,
        event_loop: Optional[asyncio.AbstractEventLoop] = None,
        button_press_callback: Optional[Callable[[int], Any]] = None,
        volume_change_callback: Optional[Callable[[int], Any]] = None,
        triple_press_callback: Optional[Callable[[], Any]] = None,
        long_press_callback: Optional[Callable[[], Any]] = None,
    ):
        self.event_loop = event_loop or asyncio.get_event_loop()
        self.button_press_callback = button_press_callback or AsyncMock()
        self.volume_change_callback = volume_change_callback or AsyncMock()
        self.triple_press_callback = triple_press_callback or AsyncMock()
        self.long_press_callback = long_press_callback or AsyncMock()
        self.last_press_time: Dict[int, float] = {}
        self.press_count: Dict[int, int] = {}
        self.volume_step = 5

    def _handle_button(self, pin: int, level: int, tick: int) -> None:
        """Simulate button press handling"""
        if callable(self.button_press_callback):
            asyncio.create_task(self.button_press_callback(pin))

    def _handle_rotation(self, pin: int, level: int, tick: int) -> None:
        """Simulate rotary encoder rotation"""
        if callable(self.volume_change_callback):
            steps = self.volume_step if pin == 1 else -self.volume_step
            asyncio.create_task(self.volume_change_callback(steps))

    def cleanup(self) -> None:
        """Cleanup mock resources"""
        pass


class MockRadioManager:
    """Mock implementation of RadioManager"""

    def __init__(self, status_update_callback: Optional[Callable] = None) -> None:
        self._status = SystemStatus(current_station=None, volume=70, is_playing=False)
        self._status_callback = status_update_callback
        self.current_station: Optional[RadioStation] = None
        self.stations: Dict[int, RadioStation] = {}
        self.volume = 70
        self.is_playing = False

    def add_station(self, station: RadioStation) -> None:
        if station.slot is not None:
            self.stations[station.slot] = station

    async def toggle_station(self, slot: int) -> bool:
        """Toggle play/pause for a specific station slot."""
        if self._status.current_station == slot and self._status.is_playing:
            self._status.current_station = None
            self._status.is_playing = False
            if self._status_callback:
                await self._status_callback(self._status.model_dump())
            return False
        else:
            self._status.current_station = slot
            self._status.is_playing = True
            if self._status_callback:
                await self._status_callback(self._status.model_dump())
            return True

    async def set_volume(self, volume: int) -> None:
        self.volume = max(0, min(100, volume))

    def get_status(self) -> SystemStatus:
        return self._status
