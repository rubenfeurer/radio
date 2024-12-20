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
        self.long_press_triggered = {}  # Track if long press was triggered
        self.monitor_tasks = {}  # Track monitoring tasks
        
        self.push_counter = 0
        self.last_push_time = 0
        self.PUSH_TIMEOUT = 2  # seconds
        self.PUSH_THRESHOLD = 4  # number of pushes needed
        
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
                    # Check the state of the other pin to determine direction
                    if self.pi.read(settings.ROTARY_DT) == 0:
                        # Clockwise rotation
                        volume_change = self.volume_step if settings.ROTARY_CLOCKWISE_INCREASES else -self.volume_step
                    else:
                        # Counter-clockwise rotation
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
        """Handle button press events."""
        try:
            current_time = time.time()
            
            # Add reset detection for rotary switch pushes
            if gpio == self.rotary_sw and level == 1:  # Button released
                # Check if we're within timeout window
                if current_time - self.last_push_time > self.PUSH_TIMEOUT:
                    self.push_counter = 0
                
                self.push_counter += 1
                self.last_push_time = current_time
                
                logger.debug(f"Push counter: {self.push_counter}")
                
                # Check if we've reached threshold
                if self.push_counter >= self.PUSH_THRESHOLD:
                    logger.info("Reset sequence detected!")
                    self.push_counter = 0  # Reset counter
                    if self.loop:
                        asyncio.run_coroutine_threadsafe(
                            self._trigger_reset(),
                            self.loop
                        )
                    return
            
            button_number = self.button_pins.get(gpio, None)
            if gpio == self.rotary_sw:
                button_number = self.rotary_sw
            
            # Button pressed (level = 0)
            if level == 0:
                # Cancel any existing monitor task for this button
                if gpio in self.monitor_tasks:
                    self.monitor_tasks[gpio].cancel()
                
                self.press_start_time[gpio] = current_time
                self.long_press_triggered[gpio] = False
                
                # Start new monitoring task
                if self.loop:
                    task = asyncio.run_coroutine_threadsafe(
                        self._monitor_long_press(gpio, button_number),
                        self.loop
                    )
                    self.monitor_tasks[gpio] = task
            
            # Button released (level = 1)
            elif level == 1 and gpio in self.press_start_time:
                # Cancel monitoring task
                if gpio in self.monitor_tasks:
                    self.monitor_tasks[gpio].cancel()
                    del self.monitor_tasks[gpio]
                
                duration = current_time - self.press_start_time[gpio]
                logger.info(f"Button {button_number} released after {duration:.2f} seconds")
                
                # Only handle short press if no long press was triggered
                if not self.long_press_triggered.get(gpio, False):
                    if duration < settings.LONG_PRESS_DURATION:
                        # Check for double press
                        if gpio in self.last_press_time:
                            time_since_last = current_time - self.last_press_time[gpio]
                            if time_since_last < settings.DOUBLE_PRESS_INTERVAL:
                                if self.double_press_callback and self.loop:
                                    logger.info(f"Double press detected on button {button_number}")
                                    asyncio.run_coroutine_threadsafe(
                                        self.double_press_callback(button_number), 
                                        self.loop
                                    )
                                    self.last_press_time[gpio] = current_time
                                    return
                            elif time_since_last < 0.5:  # 500ms debounce
                                logger.debug(f"Ignoring button {button_number} - too soon after last press ({time_since_last}s)")
                                return
                        
                        # Handle single press
                        if self.button_press_callback and self.loop:
                            logger.info(f"Single press detected on button {button_number}")
                            asyncio.run_coroutine_threadsafe(
                                self.button_press_callback(button_number), 
                                self.loop
                            )
                
                self.last_press_time[gpio] = current_time
                logger.debug(f"Updated last press time for button {button_number}")
                
        except Exception as e:
            logger.error(f"Error in button handler: {e}", exc_info=True)

    async def _monitor_long_press(self, gpio, button_number):
        """Monitor button press duration and trigger long press when threshold is met."""
        try:
            while gpio in self.press_start_time:
                current_time = time.time()
                duration = current_time - self.press_start_time[gpio]
                
                # Check if button is still pressed and duration exceeds threshold
                if (duration >= settings.LONG_PRESS_DURATION and 
                    not self.long_press_triggered.get(gpio, False)):
                    if self.long_press_callback:
                        logger.info(f"Long press threshold met for button {button_number}")
                        self.long_press_triggered[gpio] = True
                        await self.long_press_callback(button_number)
                    break  # Exit after triggering
                
                await asyncio.sleep(0.1)
                
        except asyncio.CancelledError:
            logger.debug(f"Long press monitoring cancelled for button {button_number}")
        except Exception as e:
            logger.error(f"Error monitoring long press: {e}", exc_info=True)

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

    async def _handle_button_press(self, button: int) -> None:
        """Handle button press events."""
        logger.debug(f"GPIOController received button press: {button}")
        if button in [1, 2, 3]:
            logger.info(f"Requesting toggle for station in slot {button}")
            try:
                response = requests.post(f"http://localhost:8000/api/v1/stations/{button}/toggle")
                response.raise_for_status()
            except requests.RequestException as e:
                logger.error(f"Failed to toggle station {button}: {str(e)}")
        else:
            logger.warning(f"Invalid button number received: {button}")

    async def _trigger_reset(self):
        """Trigger system reset when push sequence detected."""
        try:
            logger.info("Triggering system reset...")
            # Call the reset handler in RadioManager
            if hasattr(self, 'reset_callback') and self.reset_callback:
                await self.reset_callback()
        except Exception as e:
            logger.error(f"Error triggering reset: {e}")