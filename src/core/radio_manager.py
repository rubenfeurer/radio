from typing import Dict, Optional
from src.core.models import RadioStation, SystemStatus
from src.hardware.audio_player import AudioPlayer
from src.hardware.gpio_controller import GPIOController
from config.config import settings
from src.utils.station_loader import load_default_stations, load_assigned_stations
from src.core.station_manager import StationManager
from src.core.sound_manager import SoundManager, SystemEvent
from src.core.mode_manager import ModeManagerSingleton, NetworkMode
from src.core.wifi_manager import WiFiManager
import logging
import asyncio
import httpx
import subprocess

logger = logging.getLogger(__name__)

class RadioManager:
    def __init__(self, status_update_callback=None, test_mode=False):
        logger.info("Initializing RadioManager")
        self._station_manager = StationManager()
        self._status = SystemStatus(volume=settings.DEFAULT_VOLUME)
        self._player = AudioPlayer() if not test_mode else AsyncMock()
        self._status_update_callback = status_update_callback
        self._lock = asyncio.Lock()
        self._sound_manager = SoundManager(test_mode=test_mode)
        self._test_mode = test_mode
        self._wifi_manager = WiFiManager()
        
        if not test_mode:
            # Initialize GPIO controller with callbacks
            logger.info("Initializing GPIO controller")
            self._gpio = GPIOController(
                volume_change_callback=self._handle_volume_change,
                button_press_callback=self._handle_button_press,
                long_press_callback=self._handle_long_press,
                triple_press_callback=self._handle_triple_press,
                event_loop=asyncio.get_event_loop()
            )
            self._gpio.reset_callback = self._handle_reset_sequence

    async def initialize(self):
        """Async initialization"""
        if not self._test_mode:
            # Set initial volume
            await self.set_volume(settings.DEFAULT_VOLUME)
            # Play startup sound
            await self._handle_startup()
    
    async def _handle_startup(self):
        """Play startup sound based on network status"""
        try:
            # Check if we're in client mode and have network
            mode_manager = ModeManagerSingleton.get_instance()
            current_mode = mode_manager.detect_current_mode()
            
            if current_mode == NetworkMode.CLIENT:
                # Check network connectivity
                if await self._check_network():
                    await self._sound_manager.notify(SystemEvent.STARTUP_SUCCESS)
                else:
                    await self._sound_manager.notify(SystemEvent.STARTUP_ERROR)
            else:
                # In AP mode, just play success sound
                await self._sound_manager.notify(SystemEvent.STARTUP_SUCCESS)
                
        except Exception as e:
            logger.error(f"Startup notification failed: {e}")
            await self._sound_manager.notify(SystemEvent.STARTUP_ERROR)
    
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
            # Ensure volume is within UI bounds (0-100)
            ui_volume = max(0, min(100, volume))
            
            # Scale UI volume to system volume (30-100)
            system_volume = settings.scale_volume_to_system(ui_volume)
            
            logger.debug(f"Setting volume - UI: {ui_volume}%, System: {system_volume}%")
            
            # Set the actual system volume
            await self._player.set_volume(system_volume)
            
            # Store the UI volume in status
            self._status.volume = ui_volume
            
            logger.info(f"Volume set successfully - UI: {ui_volume}%, System: {system_volume}%")
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

    async def _handle_long_press(self, button: int) -> None:
        """Handle long press events - toggle between AP and Client mode."""
        try:
            logger.debug(f"Long press handler called for button {button}")
            logger.debug(f"Comparing with ROTARY_SW: {settings.ROTARY_SW}")
            
            # Only handle long press for rotary encoder button
            if button != settings.ROTARY_SW:
                logger.debug(f"Ignoring long press for non-rotary button (got {button}, expected {settings.ROTARY_SW})")
                return
            
            logger.info(f"Long press confirmed on rotary encoder (pin {settings.ROTARY_SW}) - initiating mode toggle")
            
            # Call the mode toggle endpoint using httpx
            async with httpx.AsyncClient() as client:
                logger.debug("Sending mode toggle request to API")
                response = await client.post('http://localhost:80/api/v1/mode/toggle')
                
                if response.status_code == 200:
                    logger.info("Mode toggle successful - mode switch initiated")
                    await self._sound_manager.notify(SystemEvent.MODE_SWITCH)
                else:
                    logger.error(f"Mode toggle failed with status {response.status_code}: {response.text}")
                    
        except Exception as e:
            logger.error(f"Error in long press handler: {str(e)}", exc_info=True)

    async def _handle_triple_press(self, button: int) -> None:
        """Handle triple press events."""
        try:
            if button == settings.ROTARY_SW:
                logger.warning("Triple press detected on rotary switch - initiating system reboot")
                # Cleanup before reboot
                await self.stop_playback()
                await self._broadcast_status()
                # Initiate reboot
                subprocess.run(['sudo', 'reboot'], check=True)
        except Exception as e:
            logger.error(f"Error in triple press handler: {e}")

    async def _handle_reset_sequence(self):
        """Handle the 4-press reset sequence."""
        try:
            logger.warning("Reset sequence detected - initiating system reset")
            
            # Stop playback
            await self.stop_playback()
            await self._broadcast_status()
            
            # Run reset script
            logger.info("Running reset_radio.sh")
            subprocess.run(['/home/radio/radio/install/reset_radio.sh'], check=True)
            
            # Restart radio service
            logger.info("Restarting radio service")
            subprocess.run(['sudo', 'systemctl', 'restart', 'radio'], check=True)
            
        except Exception as e:
            logger.error(f"Error handling reset sequence: {e}")

    async def _check_network(self) -> bool:
        """Check network connectivity using WiFiManager"""
        try:
            status = self._wifi_manager.get_current_status()
            return status.has_internet
        except Exception as e:
            logger.error(f"Network check failed: {e}")
            return False