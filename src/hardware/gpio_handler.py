import RPi.GPIO as GPIO
import logging
from time import sleep, time

logger = logging.getLogger(__name__)

class GPIOHandler:
    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GPIOHandler, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        # GPIO Pins for buttons
        self.BUTTON1_PIN = 17  # First slot control
        self.BUTTON2_PIN = 16  # Second slot control
        self.BUTTON3_PIN = 26  # Third slot control
        
        self.player = None
        self.stream_manager = None
        self.last_button_press = 0
        self.DEBOUNCE_TIME = 0.3  # 300ms debounce
        
        try:
            GPIO.setmode(GPIO.BCM)
            
            # Setup button pins
            for pin in [self.BUTTON1_PIN, self.BUTTON2_PIN, self.BUTTON3_PIN]:
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                GPIO.add_event_detect(pin, GPIO.FALLING, 
                                    callback=self.button_callback, 
                                    bouncetime=300)
            
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
        