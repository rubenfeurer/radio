import asyncio
import logging
from enum import Enum
from pathlib import Path

from mpv import MPV

from config.config import settings

logger = logging.getLogger(__name__)


class SystemEvent(Enum):
    STARTUP_SUCCESS = "startup_success"
    STARTUP_ERROR = "startup_error"
    MODE_SWITCH = "mode_switch"
    WIFI_CONNECTED = "wifi_connected"


class SoundManager:
    def __init__(self, test_mode=False):
        """Initialize SoundManager

        Args:
            test_mode (bool): If True, use test mode (no actual sounds)

        """
        self._test_mode = test_mode
        self.sound_dir = Path("/home/radio/radio/sounds")
        self.event_sounds = {
            SystemEvent.STARTUP_SUCCESS: "success.wav",
            SystemEvent.STARTUP_ERROR: "error.wav",
            SystemEvent.MODE_SWITCH: "success.wav",
            SystemEvent.WIFI_CONNECTED: "success.wav",
        }
        self._verify_sound_files()

    def _verify_sound_files(self):
        """Check if all required sound files exist"""
        for event, sound_file in self.event_sounds.items():
            sound_path = self.sound_dir / sound_file
            if not sound_path.exists():
                logger.error(f"Sound file missing for {event}: {sound_path}")
            else:
                logger.info(f"Found sound file for {event}: {sound_path}")

    async def play_sound(self, sound_file: str):
        """Play a sound file using MPV non-blocking"""
        try:
            sound_path = self.sound_dir / sound_file
            if not sound_path.exists():
                logger.error(f"Sound file not found: {sound_path}")
                return

            logger.info(
                f"Playing sound: {sound_path} at volume {settings.NOTIFICATION_VOLUME}%",
            )

            # Create temporary MPV instance for notification
            player = MPV(volume=settings.NOTIFICATION_VOLUME)

            try:
                # Play the sound without waiting
                player.play(str(sound_path))

                # Wait briefly for playback to start
                await asyncio.sleep(0.1)

                # Create task to cleanup player after sound finishes
                asyncio.create_task(self._cleanup_player(player))

            except Exception as e:
                logger.error(f"Error during playback: {e}")
                player.terminate()

        except Exception as e:
            logger.error(f"Failed to play sound {sound_file}: {e}", exc_info=True)

    async def _cleanup_player(self, player):
        """Cleanup player after sound finishes"""
        try:
            # Wait for sound to finish (with timeout)
            start_time = asyncio.get_event_loop().time()
            while player.time_pos is None or player.time_pos < player.duration:
                await asyncio.sleep(0.1)
                # Add timeout of 5 seconds
                if asyncio.get_event_loop().time() - start_time > 5:
                    logger.warning("Sound playback timeout - forcing cleanup")
                    break
        finally:
            player.terminate()
            logger.debug("Player cleanup completed")

    async def notify(self, event: SystemEvent):
        """Play notification sound for an event"""
        try:
            if event in self.event_sounds:
                sound_file = self.event_sounds[event]
                logger.info(
                    f"Playing notification for event: {event.value} using {sound_file}",
                )
                await self.play_sound(sound_file)
            else:
                logger.warning(f"No sound defined for event: {event}")
        except Exception as e:
            logger.error(f"Failed to play notification for {event}: {e}", exc_info=True)
