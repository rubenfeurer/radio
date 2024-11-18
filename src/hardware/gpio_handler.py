import RPi.GPIO as GPIO
import logging
import tomli
import time

logger = logging.getLogger(__name__)

class GPIOHandler:
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(GPIOHandler, cls).__new__(cls)
        return cls._instance

    def __init__(self, config_file='config/config.toml'):
        """Initialize GPIO handler"""
        self.player = None
        self.stream_manager = None
        self.last_button_press = 0
        self.debounce_time = 300  # Default debounce time in ms
        
        try:
            with open(config_file, 'rb') as f:
                config = tomli.load(f)
                gpio_config = config.get('gpio', {})
                self.debounce_time = gpio_config.get('settings', {}).get('debounce_time', 300)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
    
    def button_callback(self, channel):
        """Handle button press events"""
        try:
            # Check debounce
            if not self._debounce():
                return

            # Get button index and corresponding stream
            button_index = self._get_button_index(channel)
            if button_index is None:
                logger.error(f"Invalid button channel: {channel}")
                return

            # Get stream for this button
            streams = self.stream_manager.get_streams_by_slots()
            requested_stream = streams.get(button_index)
            
            if not requested_stream:
                logger.error(f"No stream configured for button {button_index}")
                return

            # Get current status
            current_status = self.player.get_status()
            current_state = current_status.get('state', 'stopped')
            current_station = current_status.get('current_station')
            
            logger.debug(f"Button press - channel: {channel}")
            logger.debug(f"Current status: {current_status}")
            logger.debug(f"Requested stream: {requested_stream}")

            # If we're playing the requested stream, stop it
            if current_state == 'playing' and current_station == requested_stream:
                logger.debug(f"Same stream playing, stopping: {current_station}")
                self.player.stop()
                return

            # If we're playing something else, stop it first
            if current_state == 'playing':
                logger.debug(f"Different stream playing, stopping before switch")
                self.player.stop()
            
            # Play the requested stream
            logger.debug(f"Playing new stream: {requested_stream}")
            self.player.play(requested_stream)

        except Exception as e:
            logger.error(f"Error in button callback: {e}")
            raise
    
    def cleanup(self):
        """Clean up GPIO resources"""
        try:
            GPIO.cleanup()
            self.__class__._instance = None
            self.__class__._initialized = False
            logger.info("GPIO cleanup completed")
        except Exception as e:
            logger.error(f"Error during GPIO cleanup: {e}")
    
    def _debounce(self):
        """Implement button debouncing"""
        current_time = int(time.time() * 1000)  # Convert to milliseconds
        if current_time - self.last_button_press < self.debounce_time:
            return False
        self.last_button_press = current_time
        return True
    
    def _get_button_index(self, channel):
        """
        Convert GPIO channel to button index (1-3)
        Args:
            channel: GPIO channel number
        Returns:
            int: Button index (1-3) or None if invalid channel
        """
        # Map GPIO pins to button indices
        pin_to_button = {
            17: 1,  # Button 1 - GPIO 17
            16: 2,  # Button 2 - GPIO 16
            26: 3   # Button 3 - GPIO 26
        }
        return pin_to_button.get(channel)
        