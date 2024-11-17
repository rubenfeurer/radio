import RPi.GPIO as GPIO
import logging
import os
import tomli
from time import time

logger = logging.getLogger(__name__)

class RotaryHandler:
    _instance = None
    _initialized = False
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(RotaryHandler, cls).__new__(cls)
        return cls._instance

    def __init__(self, config_file='config/config.toml'):
        if self._initialized:
            return
            
        try:
            # Load configuration
            with open(config_file, 'rb') as f:
                config = tomli.load(f)
            
            # Get rotary configuration
            rotary_config = config.get('rotary', {})
            self.CLK_PIN = rotary_config.get('clk_pin', 11)
            self.DT_PIN = rotary_config.get('dt_pin', 9)
            self.SW_PIN = rotary_config.get('sw_pin', 10)
            
            # Get rotary settings
            rotary_settings = rotary_config.get('settings', {})
            self.VOLUME_STEP = rotary_settings.get('volume_step', 5)
            self.DOUBLE_CLICK_TIMEOUT = rotary_settings.get('double_click_timeout', 500) / 1000  # Convert to seconds
            self.DEBOUNCE_TIME = rotary_settings.get('debounce_time', 50)
            
            # State tracking
            self.last_click_time = 0
            self.last_clk_state = None
            self.player = None
            
            self.setup_gpio()
            self._initialized = True
            logger.info("Rotary Handler initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing Rotary Handler: {str(e)}", exc_info=True)
    
    def setup_gpio(self):
        """Setup GPIO pins for rotary encoder"""
        try:
            GPIO.setmode(GPIO.BCM)
            
            # Setup pins as inputs with pull-up resistors
            GPIO.setup(self.CLK_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(self.DT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(self.SW_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            # Save initial state
            self.last_clk_state = GPIO.input(self.CLK_PIN)
            
            # Add event detection
            GPIO.add_event_detect(self.CLK_PIN, GPIO.BOTH, callback=self.clk_callback, bouncetime=self.DEBOUNCE_TIME)
            GPIO.add_event_detect(self.DT_PIN, GPIO.BOTH, callback=self.dt_callback, bouncetime=self.DEBOUNCE_TIME)
            GPIO.add_event_detect(self.SW_PIN, GPIO.FALLING, callback=self.sw_callback, bouncetime=self.DEBOUNCE_TIME)
            
        except Exception as e:
            logger.error(f"Error setting up GPIO for Rotary Handler: {str(e)}")
    
    def clk_callback(self, channel):
        """Handle clock pin changes"""
        try:
            if self.player is None:
                return
                
            clk_state = GPIO.input(self.CLK_PIN)
            dt_state = GPIO.input(self.DT_PIN)
            
            if clk_state != self.last_clk_state:
                if dt_state == clk_state:  # Clockwise rotation
                    current_volume = self.player.get_volume()
                    new_volume = min(100, current_volume + self.VOLUME_STEP)
                    self.player.set_volume(new_volume)
                    logger.debug(f"Volume increased to {new_volume}")
                
                self.last_clk_state = clk_state
                
        except Exception as e:
            logger.error(f"Error in CLK callback: {str(e)}")
    
    def dt_callback(self, channel):
        """Handle data pin changes"""
        try:
            if self.player is None:
                return
                
            clk_state = GPIO.input(self.CLK_PIN)
            dt_state = GPIO.input(self.DT_PIN)
            
            if dt_state == clk_state:  # Counter-clockwise rotation
                current_volume = self.player.get_volume()
                new_volume = max(0, current_volume - self.VOLUME_STEP)
                self.player.set_volume(new_volume)
                logger.debug(f"Volume decreased to {new_volume}")
                
        except Exception as e:
            logger.error(f"Error in DT callback: {str(e)}")
    
    def sw_callback(self, channel):
        """Handle button press"""
        try:
            current_time = time()
            time_diff = current_time - self.last_click_time
            
            if 0 < time_diff < self.DOUBLE_CLICK_TIMEOUT:
                logger.info("Double click detected, initiating reboot...")
                os.system('sudo reboot')
            
            self.last_click_time = current_time
            
        except Exception as e:
            logger.error(f"Error in button callback: {str(e)}")
    
    def cleanup(self):
        """Clean up GPIO resources"""
        try:
            GPIO.cleanup([self.CLK_PIN, self.DT_PIN, self.SW_PIN])
            self.__class__._instance = None
            self.__class__._initialized = False
            logger.info("Rotary Handler cleanup completed")
        except Exception as e:
            logger.error(f"Error during Rotary Handler cleanup: {e}")