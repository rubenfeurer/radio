import RPi.GPIO as GPIO
import logging
import os
import tomli
from time import time

logger = logging.getLogger(__name__)

class RotaryHandler:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(RotaryHandler, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, radio_player):
        """Initialize the rotary encoder handler"""
        if self._initialized:
            return
        
        self.radio_player = radio_player
        
        # Initialize instance variables first
        self.is_first_click = True
        self.last_click_time = None
        self.pending_click = False
        self.last_clk = None
        self.last_dt = None
        self.clk_callback = self._clk_callback
        self.button_callback = self._button_callback
        
        # Load config from the correct path
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', 'config.toml')
        with open(config_path, 'rb') as f:
            config = tomli.load(f)
        
        # Get GPIO pin numbers from config
        gpio_config = config['gpio']['rotary']
        self.clk_pin = gpio_config['clk']
        self.dt_pin = gpio_config['dt']
        self.sw_pin = gpio_config['sw']
        
        # Get rotary settings from config
        rotary_settings = config['rotary']['settings']
        self.CLOCKWISE_INCREASES = rotary_settings['clockwise_increases']
        self.VOLUME_STEP = rotary_settings['volume_step']
        self.DEBOUNCE_TIME = rotary_settings['debounce_time']
        self.DOUBLE_CLICK_TIMEOUT = rotary_settings['double_click_timeout']
        
        # Configure GPIO pins
        GPIO.setmode(GPIO.BCM)
        
        # Setup pins with pull-up resistors
        GPIO.setup(self.clk_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.dt_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.sw_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Get initial states after setup
        self.last_clk = GPIO.input(self.clk_pin)
        self.last_dt = GPIO.input(self.dt_pin)
        
        # Add event detection
        GPIO.add_event_detect(self.clk_pin, GPIO.BOTH, callback=self.clk_callback)
        GPIO.add_event_detect(self.sw_pin, GPIO.FALLING, callback=self.button_callback, bouncetime=300)
        
        self._initialized = True
    
    def _clk_callback(self, channel):
        """Internal clock callback implementation"""
        try:
            clk_state = GPIO.input(self.clk_pin)
            dt_state = GPIO.input(self.dt_pin)
            
            if clk_state != self.last_clk:
                # Only process on falling edge of CLK
                if self.last_clk == 1:
                    # Determine rotation direction based on DT state
                    if dt_state == 1:  # Clockwise rotation
                        if self.CLOCKWISE_INCREASES:
                            self.volume_up()
                        else:
                            self.volume_down()
                    else:  # Counter-clockwise rotation
                        if self.CLOCKWISE_INCREASES:
                            self.volume_down()
                        else:
                            self.volume_up()
                
                # Update states
                self.last_clk = clk_state
                self.last_dt = dt_state
                
        except Exception as e:
            logger.error(f"Error in rotary callback: {e}", exc_info=True)
    
    def _button_callback(self, channel):
        """Internal button callback implementation"""
        try:
            current_time = time()
            
            if not self.pending_click:
                # First click
                self.last_click_time = current_time
                self.pending_click = True
                return
            
            # Second click received
            time_diff = current_time - self.last_click_time
            if time_diff < self.DOUBLE_CLICK_TIMEOUT:
                # Valid double click
                logger.info("Double click detected, rebooting system...")
                os.system('sudo reboot')
            
            # Reset state
            self.pending_click = False
            self.last_click_time = None
            
        except Exception as e:
            logger.error(f"Error in switch callback: {e}")
            self.pending_click = False
            self.last_click_time = None
    
    def volume_up(self):
        """Increase volume by VOLUME_STEP"""
        try:
            current_volume = self.radio_player.get_volume()
            logger.debug(f"Current volume before increase: {current_volume}")
            new_volume = min(100, current_volume + self.VOLUME_STEP)
            logger.debug(f"Attempting to set new volume: {new_volume}")
            result = self.radio_player.set_volume(new_volume)
            logger.debug(f"Volume set result: {result}")
            logger.info(f"Volume up: {current_volume} -> {new_volume}")
        except Exception as e:
            logger.error(f"Error in volume_up: {e}", exc_info=True)
    
    def volume_down(self):
        """Decrease volume by VOLUME_STEP"""
        try:
            current_volume = self.radio_player.get_volume()
            logger.debug(f"Current volume before decrease: {current_volume}")
            new_volume = max(0, current_volume - self.VOLUME_STEP)
            logger.debug(f"Attempting to set new volume: {new_volume}")
            result = self.radio_player.set_volume(new_volume)
            logger.debug(f"Volume set result: {result}")
            logger.info(f"Volume down: {current_volume} -> {new_volume}")
        except Exception as e:
            logger.error(f"Error in volume_down: {e}", exc_info=True)
    
    def cleanup(self):
        """Clean up GPIO resources"""
        try:
            GPIO.cleanup([self.clk_pin, self.dt_pin, self.sw_pin])
            self.__class__._instance = None
            self.__class__._initialized = False
            logger.info("Rotary Handler cleanup completed")
        except Exception as e:
            logger.error(f"Error during Rotary Handler cleanup: {e}")
    
    def process_rotation(self, direction):
        """Process rotation direction and adjust volume"""
        try:
            current_volume = self.radio_player.get_volume()
            logger.debug(f"Current volume: {current_volume}, Direction: {direction}")
            
            # Calculate new volume
            if direction > 0:
                new_volume = min(100, current_volume + self.VOLUME_STEP)
            else:
                new_volume = max(0, current_volume - self.VOLUME_STEP)
            
            # Only set volume if it changed
            if new_volume != current_volume:
                self.radio_player.set_volume(new_volume)
                logger.info(f"Volume {'up' if direction > 0 else 'down'}: {current_volume} -> {new_volume}")
            
        except Exception as e:
            logger.error(f"Error processing rotation: {e}")

    @classmethod
    def reset_instance(cls):
        """Reset the singleton instance - mainly for testing"""
        if cls._instance is not None:
            cls._instance.cleanup()
        cls._instance = None

    def _handle_rotation(self, channel):
        """Handle rotary encoder rotation"""
        try:
            clk_state = GPIO.input(self.clk_pin)
            dt_state = GPIO.input(self.dt_pin)
            
            logger.debug(f"Rotary rotation detected - CLK: {clk_state}, DT: {dt_state}")
            
            if clk_state != self.last_clk_state:
                if dt_state != clk_state:
                    # Clockwise rotation
                    current_volume = self.radio_service.player.get_volume()
                    new_volume = min(100, current_volume + self.volume_step)
                    logger.debug(f"Volume increase: {current_volume} -> {new_volume}")
                    success = self.radio_service.player.set_volume(new_volume)
                    if success:
                        logger.info(f"Volume increased to {new_volume}%")
                    else:
                        logger.error("Failed to increase volume")
                else:
                    # Counter-clockwise rotation
                    current_volume = self.radio_service.player.get_volume()
                    new_volume = max(0, current_volume - self.volume_step)
                    logger.debug(f"Volume decrease: {current_volume} -> {new_volume}")
                    success = self.radio_service.player.set_volume(new_volume)
                    if success:
                        logger.info(f"Volume decreased to {new_volume}%")
                    else:
                        logger.error("Failed to decrease volume")
                    
            self.last_clk_state = clk_state
            
        except Exception as e:
            logger.error(f"Error handling rotation: {e}", exc_info=True)