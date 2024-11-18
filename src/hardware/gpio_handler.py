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
        
        self._initialized = True

    def setup(self, player, stream_manager):
        """Initialize with required dependencies"""
        if not player or not stream_manager:
            logger.error("Cannot setup GPIO handler: missing dependencies")
            return
            
        self.player = player
        self.stream_manager = stream_manager
        
        # Initialize stream toggler with dependencies
        self.stream_toggler = StreamToggler(player, stream_manager)
        logger.debug(f"Stream toggler initialized with player: {player}")
        
        if not self.__class__._initialized:
            self._setup_gpio()
            self.__class__._initialized = True
        
        logger.info("GPIO handler initialized")

    def _setup_gpio(self):
        """Set up GPIO pins and event detection"""
        GPIO.setmode(GPIO.BCM)
        
        try:
            # Load config
            with open('config/config.toml', 'rb') as f:
                config = tomli.load(f)
                button_config = config['gpio']['buttons']
                pin_mapping = {
                    button_config['button1']: 1,
                    button_config['button2']: 2,
                    button_config['button3']: 3
                }
        except Exception as e:
            logger.warning(f"Failed to load button config, using fallback: {e}")
            # Fallback to hardcoded pin mapping matching physical setup
            pin_mapping = {
                17: 1,  # Button 1 - GPIO 17
                16: 2,  # Button 2 - GPIO 16
                26: 3   # Button 3 - GPIO 26
            }
        
        # Setup button pins with error handling
        for pin, button_num in pin_mapping.items():
            try:
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                GPIO.add_event_detect(
                    pin,
                    GPIO.FALLING,
                    callback=self.button_callback,
                    bouncetime=300
                )
                logger.debug(f"Successfully setup GPIO pin {pin} for button {button_num}")
            except Exception as e:
                logger.error(f"Failed to setup GPIO pin {pin}: {e}")

        self.pin_mapping = pin_mapping  # Store for button_callback use

    def button_callback(self, channel):
        """Handle button press events"""
        if not self._debounce():
            return

        try:
            button_index = self.pin_mapping.get(channel)
            if button_index is None:
                logger.error(f"Invalid button channel: {channel}")
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
        