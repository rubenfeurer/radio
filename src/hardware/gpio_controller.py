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
        logger.debug(f"Rotation detected on GPIO {gpio}")
        if not self.volume_change_callback:
            return
            
        dt_state = self.pi.read(self.rotary_dt)
        volume_change = self.volume_step if dt_state else -self.volume_step
        
        if not settings.ROTARY_CLOCKWISE_INCREASES:
            volume_change = -volume_change
            
        logger.info(f"Volume change: {volume_change}")
        asyncio.create_task(self.volume_change_callback(volume_change))

    def _handle_button(self, gpio, level, tick):
        logger.debug(f"Raw button event - GPIO: {gpio}, Level: {level}, Tick: {tick}")
        if gpio in self.button_pins:
            button_number = self.button_pins[gpio]
            current_time = time.time()
            
            logger.debug(f"Processing button {button_number} (GPIO {gpio})")
            
            if level == 0:  # Button pressed down
                self.press_start_time[gpio] = current_time
                logger.debug(f"Button {button_number} pressed down at {current_time}")
            elif level == 1:  # Button released
                if gpio not in self.press_start_time:
                    logger.warning(f"Button {button_number} released but no press start time found")
                    return
                    
                press_duration = current_time - self.press_start_time[gpio]
                logger.debug(f"Button {button_number} released. Duration: {press_duration}")
                
                if press_duration > settings.LONG_PRESS_DURATION:
                    if self.long_press_callback:
                        logger.info(f"Long press detected on button {button_number}")
                        asyncio.run_coroutine_threadsafe(
                            self.long_press_callback(button_number), self.loop
                        )
                else:
                    last_press = self.last_press_time.get(gpio, 0)
                    if current_time - last_press < settings.DOUBLE_PRESS_INTERVAL:
                        if self.double_press_callback:
                            logger.info(f"Double press detected on button {button_number}")
                            asyncio.run_coroutine_threadsafe(
                                self.double_press_callback(button_number), self.loop
                            )
                    else:
                        if self.button_press_callback:
                            logger.info(f"Single press detected on button {button_number}")
                            asyncio.run_coroutine_threadsafe(
                                self.button_press_callback(button_number), self.loop
                            )
                
                self.last_press_time[gpio] = current_time
                logger.debug(f"Updated last press time for button {button_number}")

    def cleanup(self):
        if hasattr(self, 'pi') and self.pi.connected:
            self.pi.stop()
            logger.info("GPIO cleanup completed")