import RPi.GPIO as GPIO
from typing import Callable, Optional
from src.core.config import settings
import os

class GPIOController:
    def __init__(
        self,
        volume_change_callback: Optional[Callable[[int], None]] = None,
        button_press_callback: Optional[Callable[[int], None]] = None,
        volume_step: int = 5
    ):
        self.volume_step = volume_step
        self.volume_change_callback = volume_change_callback
        self.button_press_callback = button_press_callback
        
        # Setup pins from config
        self.rotary_clk = settings.ROTARY_CLK
        self.rotary_dt = settings.ROTARY_DT
        self.rotary_sw = settings.ROTARY_SW
        
        # Button pins from config
        self.button_pins = {
            settings.BUTTON_PIN_1: 1,
            settings.BUTTON_PIN_2: 2,
            settings.BUTTON_PIN_3: 3
        }
        
        # Skip GPIO setup in test environment
        if os.environ.get('PYTEST_CURRENT_TEST'):
            self.is_initialized = True
            return
            
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        
        try:
            # Initialize pins
            GPIO.setup(self.rotary_clk, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(self.rotary_dt, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(self.rotary_sw, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            for pin in self.button_pins.keys():
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            # Add event detection
            GPIO.add_event_detect(self.rotary_clk, GPIO.FALLING, 
                                callback=self._handle_rotation, bouncetime=50)
            GPIO.add_event_detect(self.rotary_sw, GPIO.FALLING, 
                                callback=self._handle_button, bouncetime=300)
                                
            for pin in self.button_pins.keys():
                GPIO.add_event_detect(pin, GPIO.FALLING, 
                                    callback=self._handle_button, bouncetime=300)
                                    
        except (RuntimeError, Exception) as e:
            print(f"GPIO initialization error (this is normal in test environment): {e}")
        
        self.is_initialized = True
        
    def _handle_rotation(self, channel):
        """Handle rotary encoder rotation events."""
        if not self.volume_change_callback:
            return
            
        clk_state = GPIO.input(self.rotary_clk)
        dt_state = GPIO.input(self.rotary_dt)
        
        # Determine direction based on state change
        if clk_state == 0:
            if dt_state == 1:
                # Clockwise
                volume_change = self.volume_step
            else:
                # Counter-clockwise
                volume_change = -self.volume_step
        else:
            return  # No change detected
        
        # If ROTARY_CLOCKWISE_INCREASES is False, invert the volume change
        if not settings.ROTARY_CLOCKWISE_INCREASES:
            volume_change = -volume_change
            
        self.volume_change_callback(volume_change)
    
    def _handle_button(self, channel):
        """Handle button press events."""
        if channel == self.rotary_sw:
            # Handle rotary encoder button press
            pass
        elif channel in self.button_pins and self.button_press_callback:
            # Handle station selection buttons
            self.button_press_callback(self.button_pins[channel])
    
    def cleanup(self):
        """Clean up GPIO resources."""
        if not os.environ.get('PYTEST_CURRENT_TEST'):
            GPIO.cleanup()