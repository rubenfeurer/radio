import logging
from src.utils.stream_manager import StreamManager
from src.player.radio_player import RadioPlayer
from src.hardware.gpio_handler import GPIOHandler

logger = logging.getLogger(__name__)

class RadioService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RadioService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        logger.info("Initializing RadioService...")
        
        try:
            # Initialize components
            self.stream_manager = StreamManager()
            self.player = RadioPlayer()
            self.gpio_handler = GPIOHandler()
            
            # Set up dependencies
            logger.info("Setting up GPIO handler dependencies...")
            self.gpio_handler.player = self.player
            self.gpio_handler.stream_manager = self.stream_manager
            
            logger.info("RadioService initialization complete")
            logger.info(f"GPIO handler initialized with player: {self.gpio_handler.player}")
            logger.info(f"GPIO handler initialized with stream manager: {self.gpio_handler.stream_manager}")
            
            self._initialized = True
        except Exception as e:
            logger.error(f"Error initializing RadioService: {e}", exc_info=True)
            raise

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