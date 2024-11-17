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
        if self._initialized:
            return
            
        self.logger = logging.getLogger(__name__)
        self.last_button_press = 0
        self.debounce_time = 300
        
        # Define button pins and mapping
        self.BUTTON1_PIN = 17
        self.BUTTON2_PIN = 16
        self.BUTTON3_PIN = 26
        
        self.channel_to_button = {
            self.BUTTON1_PIN: 1,
            self.BUTTON2_PIN: 2,
            self.BUTTON3_PIN: 3
        }
        
        self._initialized = True
    
    def button_callback(self, channel):
        """Callback function for button press"""
        if not self._debounce():
            return
        
        try:
            button_number = self.channel_to_button.get(channel)
            if button_number is None:
                self.logger.error(f"Invalid channel: {channel}")
                return
            
            streams = self.stream_manager.get_streams_by_slots()
            stream = streams.get(button_number)
            if not stream:
                self.logger.error(f"No stream configured for button {button_number}")
                return

            # Get current status
            current_status = self.player.get_status()
            print(f"DEBUG: Current status: {current_status}")
            
            current_state = current_status.get('state', 'stopped')
            current_station = current_status.get('current_station')
            
            print(f"DEBUG: Current state: {current_state}, station: {current_station}")
            print(f"DEBUG: Requested stream: {stream}")

            # If the same stream is currently playing, stop it
            if current_state == 'playing' and current_station == stream:
                print("DEBUG: Same stream playing, stopping it")
                self.player.stop()
                return

            # If a different stream is playing, stop it first
            if current_state == 'playing':
                print("DEBUG: Different stream playing, stopping before switch")
                self.player.stop()

            # Only play if we're not stopping the current stream
            if current_state == 'stopped' or current_station != stream:
                print(f"DEBUG: Playing stream: {stream}")
                self.player.play(stream)
                
        except Exception as e:
            self.logger.error(f"Error handling button press: {e}")
    
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
        