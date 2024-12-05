from typing import Dict, Optional
from src.core.models import RadioStation, SystemStatus
from src.hardware.audio_player import AudioPlayer
from src.hardware.gpio_controller import GPIOController
from config.config import settings
from src.utils.station_loader import load_default_stations
import logging
import asyncio

logger = logging.getLogger(__name__)

class RadioManager:
    def __init__(self, status_update_callback=None):
        logger.info("Initializing RadioManager")
        self._stations: Dict[int, RadioStation] = {}
        self._status = SystemStatus(volume=settings.DEFAULT_VOLUME)
        self._player = AudioPlayer()
        self._status_update_callback = status_update_callback
        
        # Initialize with default stations
        logger.info("Loading default stations")
        self._load_default_stations()
        
        # Get the current event loop
        self.loop = asyncio.get_event_loop()
        
        # Initialize GPIO controller with callbacks
        logger.info("Initializing GPIO controller")
        self._gpio = GPIOController(
            volume_change_callback=self._handle_volume_change,
            button_press_callback=self._handle_button_press,
            event_loop=self.loop  # Pass the event loop
        )
        logger.info("GPIO controller initialized")
        
        self.current_slot = None
        self.is_playing = False
        logger.info("RadioManager initialization complete")
        
    def _load_default_stations(self) -> None:
        """Load default stations into empty slots"""
        default_stations = load_default_stations()
        
        # Add default stations to empty slots
        for slot, station in default_stations.items():
            if slot not in self._stations:
                self._stations[slot] = station
                logger.info(f"Added default station to slot {slot}: {station.name}")
    
    async def _handle_volume_change(self, change: int) -> None:
        """Handle volume change from rotary encoder."""
        current_volume = self._status.volume
        new_volume = max(0, min(100, current_volume + change))
        await self.set_volume(new_volume)
    
    async def _handle_button_press(self, button: int) -> None:
        """Handle button press events."""
        logger.debug(f"RadioManager received button press: {button}")
        if button in [1, 2, 3]:
            logger.info(f"Toggling station in slot {button}")
            await self.toggle_station(button)
        else:
            logger.warning(f"Invalid button number received: {button}")
    
    def add_station(self, station: RadioStation) -> None:
        """Override existing station in slot"""
        if station.slot is not None:
            self._stations[station.slot] = station
            logger.info(f"Updated station in slot {station.slot}: {station.name}")
    
    def remove_station(self, slot: int) -> None:
        if slot in self._stations:
            del self._stations[slot]
            if self._status.current_station == slot:
                self._status.current_station = None
                self._status.is_playing = False
                
    def get_station(self, slot: int) -> Optional[RadioStation]:
        return self._stations.get(slot)
        
    async def play_station(self, slot: int) -> None:
        if slot in self._stations:
            station = self._stations[slot]
            await self._player.play(station.url)
            self._status.current_station = slot
            self._status.is_playing = True
            
    async def stop_playback(self) -> None:
        await self._player.stop()
        self._status.is_playing = False
        
    def get_status(self) -> SystemStatus:
        return self._status
        
    async def set_volume(self, volume: int) -> None:
        await self._player.set_volume(volume)
        self._status.volume = volume
        await self._broadcast_status()  # Broadcast volume changes too
        
    async def toggle_station(self, slot: int) -> bool:
        """Toggle play/pause for a specific station slot."""
        station = self.get_station(slot)
        if not station:
            raise ValueError(f"No station found in slot {slot}")

        # If this slot is currently playing, pause it
        if self.current_slot == slot and self.is_playing:
            await self.stop_playback()
            self.is_playing = False
            self.current_slot = None
            logger.info(f"Stopped playing station in slot {slot}")
            result = False
        else:
            # If another slot is playing, stop it first
            if self.is_playing:
                await self.stop_playback()
                logger.info(f"Stopped playing station in slot {self.current_slot}")

            # Play the requested station
            await self.play_station(slot)
            self.is_playing = True
            self.current_slot = slot
            logger.info(f"Started playing station in slot {slot}")
            result = True

        # Broadcast the status update
        await self._broadcast_status()
        return result

    async def _broadcast_status(self):
        """Broadcast current status to all connected clients"""
        if self._status_update_callback:
            status_dict = self._status.model_dump()
            status_dict["current_station"] = self.current_slot
            status_dict["is_playing"] = self.is_playing
            await self._status_update_callback(status_dict)