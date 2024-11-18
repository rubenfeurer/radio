import RPi.GPIO as GPIO
import logging
import tomli
import time
from .button_handler import ButtonMapper, ButtonStateHandler, StreamToggler, ButtonPress

logger = logging.getLogger(__name__)

class GPIOHandler:
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(GPIOHandler, cls).__new__(cls)
            cls._instance._initialized = False
            cls._instance.player = None
            cls._instance.stream_manager = None
            cls._instance.button_state = ButtonStateHandler()
            cls._instance.stream_toggler = None
            cls._instance.last_button_press = 0
            cls._instance.debounce_time = 300  # milliseconds
        return cls._instance

    def __init__(self, config_file='config/config.toml'):
        """Initialize GPIO handler"""
        if self._initialized:
            return
            
        self.player = None
        self.stream_manager = None
        self.button_state = ButtonStateHandler()
        self.stream_toggler = None
        self.last_button_press = 0
        self.debounce_time = 300  # milliseconds
        
        try:
            with open(config_file, 'rb') as f:
                config = tomli.load(f)
                gpio_config = config.get('gpio', {})
                self.debounce_time = gpio_config.get('settings', {}).get('debounce_time', 300)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
        
        # Remove this line - initialization should happen in setup()
        # self._initialized = True

    def setup(self, player, stream_manager):
        """Set up GPIO handler with dependencies"""
        try:
            # Initialize GPIO mode first
            GPIO.setmode(GPIO.BCM)
            
            self.player = player
            self.stream_manager = stream_manager
            self.stream_toggler = StreamToggler(player, stream_manager)
            
            # Initialize pin mapping
            try:
                # Load config
                with open('config/config.toml', 'rb') as f:
                    config = tomli.load(f)
                    button_config = config['gpio']['buttons']
                    self.pin_mapping = {
                        button_config['button1']: 1,
                        button_config['button2']: 2,
                        button_config['button3']: 3
                    }
            except Exception as e:
                logger.warning(f"Failed to load button config, using fallback: {e}")
                # Fallback to hardcoded pin mapping matching physical setup
                self.pin_mapping = {
                    17: 1,  # Button 1 - GPIO 17
                    16: 2,  # Button 2 - GPIO 16
                    26: 3   # Button 3 - GPIO 26
                }
            
            # Setup button pins
            for pin in self.pin_mapping.keys():
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                GPIO.add_event_detect(
                    pin,
                    GPIO.FALLING,
                    callback=self.button_callback,
                    bouncetime=self.debounce_time
                )
            
            logger.info("GPIO handler initialized successfully")
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Error setting up GPIO handler: {e}")
            self._initialized = False
            raise

    def button_callback(self, channel):
        """Handle button press events"""
        if not self._debounce():
            logger.debug("Debounce prevented button press")
            return

        try:
            button_index = self.pin_mapping.get(channel)
            if button_index is None:
                logger.error(f"Invalid button channel: {channel}")
                return

            if self.stream_toggler is None:
                logger.error("Stream toggler not initialized")
                return

            button_press = ButtonPress(channel=channel, button_index=button_index)
            logger.debug(f"Processing button press: {button_press}")
            self.stream_toggler.handle_button_press(button_press)
        except Exception as e:
            logger.error(f"Error in button callback: {e}", exc_info=True)
    
    def cleanup(self):
        """Clean up GPIO resources"""
        try:
            GPIO.cleanup()
            # Reset instance variables
            self.player = None
            self.stream_manager = None
            self.stream_toggler = None
            self.last_button_press = 0
            # Reset singleton state properly
            self._initialized = False
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
        button_index = pin_to_button.get(channel)
        logger.debug(f"Converting channel {channel} to button index: {button_index}")
        return button_index
        