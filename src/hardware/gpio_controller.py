import pigpio
from typing import Optional, Callable
import asyncio
from src.utils.logger import logger
from config.config import settings
import time

class GPIOController:
    def __init__(
        self,
        volume_change_callback: Optional[Callable[[int], None]] = None,
        button_press_callback: Optional[Callable[[int], None]] = None,
        long_press_callback: Optional[Callable[[int], None]] = None,
        double_press_callback: Optional[Callable[[int], None]] = None,
        volume_step: int = settings.ROTARY_VOLUME_STEP,
        event_loop: asyncio.AbstractEventLoop = None
    ):
        logger.info("Initializing GPIOController with pigpio")
        self.volume_step = volume_step
        self.volume_change_callback = volume_change_callback
        self.button_press_callback = button_press_callback
        self.long_press_callback = long_press_callback
        self.double_press_callback = double_press_callback
        self.loop = event_loop
        
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
        
        # Track button press times
        self.last_press_time = {}
        self.press_start_time = {}
        
        try:
            # Initialize pigpio
            self.pi = pigpio.pi()
            if not self.pi.connected:
                logger.error("Failed to connect to pigpio daemon")
                return
                
            logger.info("Connected to pigpio daemon")
            
            # Setup rotary encoder pins
            self.pi.set_mode(self.rotary_clk, pigpio.INPUT)
            self.pi.set_mode(self.rotary_dt, pigpio.INPUT)
            self.pi.set_mode(self.rotary_sw, pigpio.INPUT)
            
            # Enable pull-up resistors
            self.pi.set_pull_up_down(self.rotary_clk, pigpio.PUD_UP)
            self.pi.set_pull_up_down(self.rotary_dt, pigpio.PUD_UP)
            self.pi.set_pull_up_down(self.rotary_sw, pigpio.PUD_UP)
            
            # Setup button pins
            for pin in self.button_pins.keys():
                self.pi.set_mode(pin, pigpio.INPUT)
                self.pi.set_pull_up_down(pin, pigpio.PUD_UP)
            
            # Setup callbacks with EITHER_EDGE instead of FALLING_EDGE
            self.pi.callback(self.rotary_clk, pigpio.EITHER_EDGE, self._handle_rotation)
            self.pi.callback(self.rotary_sw, pigpio.EITHER_EDGE, self._handle_button)
            
            for pin in self.button_pins.keys():
                self.pi.callback(pin, pigpio.EITHER_EDGE, self._handle_button)
                
            logger.info("GPIO initialization completed successfully")
            
        except Exception as e:
            logger.error(f"GPIO initialization failed: {str(e)}")
            if hasattr(self, 'pi') and self.pi.connected:
                self.pi.stop()
            raise

    def _handle_rotation(self, gpio, level, tick):
        """Handle rotary encoder rotation events."""
        try:
            logger.debug(f"Rotation detected on GPIO {gpio}")
            if gpio == settings.ROTARY_CLK:
                if level == 1:
                    if self.pi.read(settings.ROTARY_DT) == 0:
                        volume_change = self.volume_step if settings.ROTARY_CLOCKWISE_INCREASES else -self.volume_step
                    else:
                        volume_change = -self.volume_step if settings.ROTARY_CLOCKWISE_INCREASES else self.volume_step
                    logger.info(f"Volume change: {volume_change}")
                    
                    if self.volume_change_callback and self.loop:
                        asyncio.run_coroutine_threadsafe(
                            self.volume_change_callback(volume_change),
                            self.loop
                        )
        except Exception as e:
            logger.error(f"Error handling rotation: {e}")

    def _handle_button(self, gpio, level, tick):
        """Handle button press/release events."""
        try:
            # Only process if it's a button pin
            if gpio not in self.button_pins:
                return
            
            button_number = self.button_pins[gpio]
            current_time = time.time()
            
            logger.debug(f"Raw button event - GPIO: {gpio}, Level: {level}, Tick: {tick}")
            
            # Button pressed (level = 0)
            if level == 0:
                self.press_start_time[gpio] = current_time
                logger.debug(f"Button {button_number} pressed down at {current_time}")
                
            # Button released (level = 1)
            elif level == 1 and gpio in self.press_start_time:
                duration = current_time - self.press_start_time[gpio]
                logger.debug(f"Button {button_number} released. Duration: {duration}")
                
                # Debounce: Ignore if last press was too recent
                if gpio in self.last_press_time:
                    time_since_last = current_time - self.last_press_time[gpio]
                    if time_since_last < 0.5:  # 500ms debounce
                        logger.debug(f"Ignoring button {button_number} - too soon after last press ({time_since_last}s)")
                        return
                
                # Handle single press
                if duration < settings.LONG_PRESS_DURATION:
                    if self.button_press_callback and self.loop:
                        logger.info(f"Single press detected on button {button_number}")
                        asyncio.run_coroutine_threadsafe(
                            self.button_press_callback(button_number), 
                            self.loop
                        )
                
                self.last_press_time[gpio] = current_time
                logger.debug(f"Updated last press time for button {button_number}")
                
        except Exception as e:
            logger.error(f"Error handling button event: {e}")

    def _handle_rotary_turn(self, way):
        """Handle rotary encoder rotation events."""
        try:
            logger.debug(f"Rotary encoder turned: {way}")
            if self.volume_change_callback and self.loop:
                # Convert rotation to volume change
                volume_change = 5 if way == 1 else -5
                logger.info(f"Processing volume change: {volume_change}")
                asyncio.run_coroutine_threadsafe(
                    self.volume_change_callback(volume_change),
                    self.loop
                )
        except Exception as e:
            logger.error(f"Error handling rotary turn: {e}")

    def cleanup(self):
        if hasattr(self, 'pi') and self.pi.connected:
            self.pi.stop()
            logger.info("GPIO cleanup completed")