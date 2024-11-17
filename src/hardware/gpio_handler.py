import RPi.GPIO as GPIO
import logging
import tomli
from time import sleep, time

logger = logging.getLogger(__name__)

class GPIOHandler:
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(GPIOHandler, cls).__new__(cls)
        return cls._instance

    def __init__(self, config_file='config/config.toml'):
        if self._initialized:
            return
            
        try:
            # Load configuration
            with open(config_file, 'rb') as f:
                config = tomli.load(f)
            
            # Get GPIO configuration
            gpio_config = config.get('gpio', {})
            self.BUTTON1_PIN = gpio_config.get('button_1_pin', 17)
            self.BUTTON2_PIN = gpio_config.get('button_2_pin', 16)
            self.BUTTON3_PIN = gpio_config.get('button_3_pin', 26)
            
            # Get GPIO settings
            gpio_settings = gpio_config.get('settings', {})
            self.DEBOUNCE_TIME = gpio_settings.get('debounce_time', 300)
            pull_up = gpio_settings.get('pull_up', True)
            
            self.player = None
            self.stream_manager = None
            self.last_button_press = 0
            
            GPIO.setmode(GPIO.BCM)
            
            # Setup button pins
            pull_up_down = GPIO.PUD_UP if pull_up else GPIO.PUD_DOWN
            for pin in [self.BUTTON1_PIN, self.BUTTON2_PIN, self.BUTTON3_PIN]:
                GPIO.setup(pin, GPIO.IN, pull_up_down=pull_up_down)
                GPIO.add_event_detect(pin, GPIO.FALLING, 
                                    callback=self.button_callback, 
                                    bouncetime=self.DEBOUNCE_TIME)
            
            logger.info("GPIO Handler initialized successfully")
            logger.info(f"Initial pin states - Button1: {GPIO.input(self.BUTTON1_PIN)}, "
                       f"Button2: {GPIO.input(self.BUTTON2_PIN)}, "
                       f"Button3: {GPIO.input(self.BUTTON3_PIN)}")
            
            self._initialized = True
            
        except Exception as e:
            logger.error(f"Error initializing GPIO Handler: {str(e)}", exc_info=True)
    
    def button_callback(self, channel):
        """Handle button press events"""
        try:
            current_status = self.player.get_status()
            streams = self.stream_manager.get_streams_by_slots()
            
            if not streams:
                logger.warning("No streams available")
                return
            
            # Map GPIO pins to stream slots
            button_to_slot = {
                17: 0,  # Button 1 -> First stream
                16: 1,  # Button 2 -> Second stream
                26: 2   # Button 3 -> Third stream
            }
            
            slot = button_to_slot.get(channel)
            if slot is None or slot >= len(streams):
                logger.warning(f"Invalid button channel: {channel}")
                return
            
            stream = streams[slot]
            
            if current_status['state'] == 'playing':
                if current_status['current_station'] == stream['url']:
                    self.player.stop()
                else:
                    # Stop current stream before playing new one
                    self.player.stop()
                    self.player.play(stream['url'])
            else:
                self.player.play(stream['url'])
            
        except Exception as e:
            logger.error(f"Error in button callback: {e}")
    
    def cleanup(self):
        """Clean up GPIO resources"""
        try:
            GPIO.cleanup()
            self.__class__._instance = None
            self.__class__._initialized = False
            logger.info("GPIO cleanup completed")
        except Exception as e:
            logger.error(f"Error during GPIO cleanup: {e}")
        