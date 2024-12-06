from typing import Dict, Optional
from src.core.models import RadioStation, SystemStatus
from src.hardware.audio_player import AudioPlayer
from src.hardware.gpio_controller import GPIOController
from config.config import settings
from src.utils.station_loader import load_default_stations, load_assigned_stations
from src.core.station_manager import StationManager
import logging
import asyncio

logger = logging.getLogger(__name__)

class RadioManager:
    def __init__(self, status_update_callback=None):
        logger.info("Initializing RadioManager")
        self._station_manager = StationManager()
        self._status = SystemStatus(volume=settings.DEFAULT_VOLUME)
        self._player = AudioPlayer()
        self._status_update_callback = status_update_callback
        self._lock = asyncio.Lock()
        
        # Get the current event loop
        self.loop = asyncio.get_event_loop()
        
        # Initialize GPIO controller with callbacks
        logger.info("Initializing GPIO controller")
        self._gpio = GPIOController(
            volume_change_callback=self._handle_volume_change,
            button_press_callback=self._handle_button_press,
            event_loop=self.loop
        )
        logger.info("GPIO controller initialized")
        logger.info("RadioManager initialization complete")
        
    def get_station(self, slot: int) -> Optional[RadioStation]:
        return self._station_manager.get_station(slot)
    
    def add_station(self, station: RadioStation) -> None:
        self._station_manager.save_station(station)
    
    async def _handle_volume_change(self, change: int) -> None:
        """Handle volume change from rotary encoder."""
        try:
            logger.debug(f"Received volume change request: {change}")
            current_volume = self._status.volume
            new_volume = max(0, min(100, current_volume + change))
            logger.info(f"Adjusting volume from {current_volume} to {new_volume}")
            
            if new_volume != current_volume:
                await self.set_volume(new_volume)
                logger.info(f"Volume set to {new_volume}")
        except Exception as e:
            logger.error(f"Error in volume change handler: {e}")
    
    async def _handle_button_press(self, button: int) -> None:
        """Handle button press events."""
        logger.info(f"Button press handler called for button {button}")
        logger.info(f"Current state - playing: {self._status.is_playing}, station: {self._status.current_station}")
        
        if button in [1, 2, 3]:
            try:
                logger.info(f"Attempting to toggle station {button}")
                result = await self.toggle_station(button)
                logger.info(f"Toggle result for station {button}: {'playing' if result else 'stopped'}")
            except Exception as e:
                logger.error(f"Error in button press handler: {e}")
        else:
            logger.warning(f"Invalid button number: {button}")
    
    async def play_station(self, slot: int) -> None:
        """Play a station and update status"""
        if slot in self._station_manager.get_all_stations():
            station = self._station_manager.get_all_stations()[slot]
            await self._player.play(station.url)
            self._status.current_station = slot
            self._status.is_playing = True
            await self._broadcast_status()
    
    async def stop_playback(self) -> None:
        await self._player.stop()
        self._status.is_playing = False
        self._status.current_station = None
        
    def get_status(self) -> SystemStatus:
        return self._status
        
    async def set_volume(self, volume: int) -> None:
        """Set system volume level."""
        try:
            logger.debug(f"Setting volume to {volume}")
            await self._player.set_volume(volume)
            self._status.volume = volume
            logger.info(f"Volume set successfully to {volume}")
            await self._broadcast_status()
        except Exception as e:
            logger.error(f"Error setting volume: {e}")
            raise
    
    async def toggle_station(self, slot: int) -> bool:
        """Toggle play/pause for a specific station slot."""
        async with self._lock:
            try:
                logger.info(f"Toggle station called for slot {slot}")
                logger.info(f"Current state - playing: {self._status.is_playing}, station: {self._status.current_station}")
                
                station = self.get_station(slot)
                if not station:
                    logger.error(f"No station found in slot {slot}")
                    raise ValueError(f"No station found in slot {slot}")

                # If this slot is currently playing, stop it
                if self._status.current_station == slot and self._status.is_playing:
                    logger.info(f"Stopping currently playing station {slot}")
                    await self.stop_playback()
                    result = False
                else:
                    # If any station is playing, stop it first
                    if self._status.is_playing:
                        logger.info(f"Stopping current playing station {self._status.current_station}")
                        await self.stop_playback()

                    # Play the requested station
                    await self.play_station(slot)
                    logger.info(f"Started playing station in slot {slot}")
                    result = True

                # Update status
                self._status.current_station = slot if result else None
                self._status.is_playing = result

                # Broadcast the status update
                await self._broadcast_status()
                logger.info(f"Updated status: playing={self._status.is_playing}, current_station={self._status.current_station}")
                return result
                
            except Exception as e:
                logger.error(f"Error in toggle_station: {e}")
                raise

    async def _broadcast_status(self):
        """Broadcast current status to all connected clients"""
        if self._status_update_callback:
            status_dict = self._status.model_dump()
            await self._status_update_callback(status_dict)
            logger.debug(f"Broadcasting status update: {status_dict}")