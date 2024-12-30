from unittest.mock import Mock, AsyncMock
import asyncio
from typing import Optional, Callable, Any
from src.core.models import RadioStation, SystemStatus

class MockAudioPlayer:
    """Mock implementation of AudioPlayer"""
    def __init__(self):
        self.volume = 70
        self.current_url = None
        self.is_playing = False
        self.mpv_instance = Mock()
        self.mpv_instance.volume = self.volume

    async def play(self, url: str) -> None:
        self.current_url = url
        self.is_playing = True
        self.mpv_instance.play.assert_called_with(url)

    async def stop(self) -> None:
        self.is_playing = False
        self.current_url = None
        self.mpv_instance.stop.assert_called_once()

    async def set_volume(self, volume: int) -> None:
        self.volume = max(0, min(100, volume))
        self.mpv_instance.volume = self.volume

class MockGPIOController:
    """Mock implementation of GPIOController"""
    def __init__(self, 
                 event_loop: Optional[asyncio.AbstractEventLoop] = None,
                 button_press_callback: Optional[Callable] = None,
                 volume_change_callback: Optional[Callable] = None,
                 triple_press_callback: Optional[Callable] = None,
                 long_press_callback: Optional[Callable] = None):
        self.event_loop = event_loop or asyncio.get_event_loop()
        self.button_press_callback = button_press_callback or AsyncMock()
        self.volume_change_callback = volume_change_callback or AsyncMock()
        self.triple_press_callback = triple_press_callback or AsyncMock()
        self.long_press_callback = long_press_callback or AsyncMock()
        self.last_press_time = {}
        self.press_count = {}
        self.volume_step = 5

    def _handle_button(self, pin: int, level: int, tick: int) -> None:
        """Simulate button press handling"""
        if self.button_press_callback:
            asyncio.create_task(self.button_press_callback(pin))

    def _handle_rotation(self, pin: int, level: int, tick: int) -> None:
        """Simulate rotary encoder rotation"""
        if self.volume_change_callback:
            steps = self.volume_step if pin == 1 else -self.volume_step
            asyncio.create_task(self.volume_change_callback(steps))

    def cleanup(self) -> None:
        """Cleanup mock resources"""
        pass

class MockRadioManager:
    """Mock implementation of RadioManager"""
    def __init__(self, status_update_callback: Optional[Callable] = None):
        self.current_station: Optional[RadioStation] = None
        self.stations = {}
        self.volume = 70
        self.is_playing = False
        self.status_update_callback = status_update_callback or AsyncMock()

    def add_station(self, station: RadioStation) -> None:
        self.stations[station.slot] = station

    async def toggle_station(self, slot: int) -> None:
        if slot in self.stations:
            if self.current_station and self.current_station.slot == slot:
                self.is_playing = not self.is_playing
            else:
                self.current_station = self.stations[slot]
                self.is_playing = True
        await self._notify_status_update()

    async def set_volume(self, volume: int) -> None:
        self.volume = max(0, min(100, volume))
        await self._notify_status_update()

    async def _notify_status_update(self) -> None:
        if self.status_update_callback:
            status = SystemStatus(
                is_playing=self.is_playing,
                current_station=self.current_station.slot if self.current_station else None,
                volume=self.volume
            )
            await self.status_update_callback(status)

    def get_status(self) -> SystemStatus:
        return SystemStatus(
            is_playing=self.is_playing,
            current_station=self.current_station.slot if self.current_station else None,
            volume=self.volume
        ) 