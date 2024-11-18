import logging
from src.utils.stream_manager import StreamManager
from src.player.radio_player import RadioPlayer
from src.hardware.gpio_handler import GPIOHandler
from src.hardware.rotary_handler import RotaryHandler
from src.utils.sound_player import SoundPlayer
import time

logger = logging.getLogger(__name__)

class RadioService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RadioService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize the radio service"""
        try:
            # Initialize components
            self.player = RadioPlayer()
            self.stream_manager = StreamManager()
            self.gpio_handler = GPIOHandler()
            
            # Setup GPIO handler with player and stream manager
            self.gpio_handler.setup(self.player, self.stream_manager)
            
            # Preload streams and play success sound only if preload succeeds
            if self._preload_streams():
                self._play_init_sound()
            
            logger.info("Radio service initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing radio service: {str(e)}")
            raise

    def _preload_streams(self):
        """Preload all streams from radio_state.json
        Returns:
            bool: True if all streams were preloaded successfully, False otherwise
        """
        try:
            logger.info("Preloading streams...")
            streams = self.stream_manager.get_streams_by_slots()
            success = True
            
            # Handle the streams dictionary
            for slot, stream in streams.items():
                try:
                    # Create media object but don't play
                    media = self.player.instance.media_new(stream)
                    # Parse media to resolve DNS and verify stream
                    media.parse()
                    logger.info(f"Preloaded stream for slot {slot}: {stream}")
                except Exception as e:
                    logger.warning(f"Failed to preload stream for slot {slot}: {e}")
                    success = False
                
                # Small delay between preloads to prevent overwhelming network
                time.sleep(0.5)
            
            if success:
                logger.info("Stream preloading completed successfully")
                return True
            else:
                logger.warning("Stream preloading completed with some failures")
                return False
            
        except Exception as e:
            logger.warning(f"Stream preloading failed: {e}")
            return False

    def _play_init_sound(self):
        """Play initialization sound using existing VLC instance"""
        try:
            success_sound = self.player.instance.media_new("/home/radio/internetRadio/sounds/success.wav")
            self.player.player.set_media(success_sound)
            self.player.player.play()
            time.sleep(0.5)  # Brief wait for sound to play
        except Exception as e:
            logger.error(f"Error playing initialization sound: {e}")

    def cleanup(self):
        """Clean up resources when shutting down"""
        logger.info("Cleaning up radio service...")
        if hasattr(self, 'player'):
            self.player.cleanup()
        if hasattr(self, 'gpio_handler'):
            self.gpio_handler.cleanup()
        logger.info("Cleanup complete")

    def get_status(self):
        """Get current player status"""
        if hasattr(self, 'player'):
            return self.player.get_status()
        return {"state": "error", "message": "Player not initialized"} 