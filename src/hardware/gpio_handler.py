import RPi.GPIO as GPIO
from src.player.radio_player import RadioPlayer
from src.utils.state_manager import StateManager
import logging

logger = logging.getLogger(__name__)

class GPIOHandler:
    def __init__(self):
        self.player = RadioPlayer()
        self.state_manager = StateManager()
        
        # GPIO Setup
        self.BUTTON_PINS = {
            'button1': 17,  # GPIO17
            'button2': 16,  # GPIO16
            'button3': 26   # GPIO26
        }
        
        self.setup_gpio()
        
    def setup_gpio(self):
        GPIO.setmode(GPIO.BCM)
        for pin in self.BUTTON_PINS.values():
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(pin, GPIO.FALLING, 
                                callback=self.button_callback, 
                                bouncetime=300)
    
    def button_callback(self, channel):
        try:
            # Get button index (0-2) based on which pin was triggered
            button_index = list(self.BUTTON_PINS.values()).index(channel)
            
            # Get selected stations
            stations = self.state_manager.get_selected_stations()
            if not stations or button_index >= len(stations):
                logger.warning(f"No station configured for button {button_index + 1}")
                return
                
            station = stations[button_index]
            current_status = self.player.get_status()
            
            # If this station is currently playing, stop it
            if (current_status["state"] == "playing" and 
                current_status["current_station"] == station["url"]):
                self.player.stop()
            # If another station is playing or nothing is playing, play this station
            else:
                self.player.play(station["url"])
                
        except Exception as e:
            logger.error(f"Error in button callback: {e}")
    
    def cleanup(self):
        GPIO.cleanup() 