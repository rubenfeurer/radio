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
        triple_press_callback: Optional[Callable[[int], None]] = None,
        volume_step: int = settings.ROTARY_VOLUME_STEP,
        event_loop: asyncio.AbstractEventLoop = None
    ):
        logger.info("Initializing GPIOController with pigpio")
        self.volume_step = volume_step
        self.volume_change_callback = volume_change_callback
        self.button_press_callback = button_press_callback
        self.long_press_callback = long_press_callback
        self.triple_press_callback = triple_press_callback
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
        
        self.press_count = {}  # Add press counter
        self.TRIPLE_PRESS_INTERVAL = 0.5  # Time window for triple press in seconds
        
        # Add these constants
        self.LONG_PRESS_DURATION = settings.LONG_PRESS_DURATION  # e.g., 2 seconds
        
        # Add state tracking for rotary encoder
        self.last_clk_state = None
        self.last_rotation_time = 0
        self.ROTATION_DEBOUNCE = 0.01  # 10ms debounce for rotation
        
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
        """Handle rotary encoder rotation events with improved state tracking."""
        try:
            current_time = time.time()
            
            # Debounce fast rotations
            if current_time - self.last_rotation_time < self.ROTATION_DEBOUNCE:
                return
                
            if gpio == settings.ROTARY_CLK:
                clk_state = level
                dt_state = self.pi.read(settings.ROTARY_DT)
                
                # Only process on rising edge of CLK
                if clk_state == 1:
                    # Determine direction based on DT state
                    if dt_state == 0:
                        # Clockwise rotation
                        volume_change = self.volume_step if settings.ROTARY_CLOCKWISE_INCREASES else -self.volume_step
                    else:
                        # Counter-clockwise rotation
                        volume_change = -self.volume_step if settings.ROTARY_CLOCKWISE_INCREASES else self.volume_step
                        
                    logger.debug(f"Rotation detected - CLK: {clk_state}, DT: {dt_state}, Change: {volume_change}")
                    
                    if self.volume_change_callback and self.loop:
                        asyncio.run_coroutine_threadsafe(
                            self.volume_change_callback(volume_change),
                            self.loop
                        )
                    
                    self.last_rotation_time = current_time
                
        except Exception as e:
            logger.error(f"Error handling rotation: {e}")

    def _handle_button(self, gpio, level, tick):
        """Handle button press events."""
        try:
            current_time = time.time()
            
            button_number = self.button_pins.get(gpio, None)
            is_rotary_switch = gpio == self.rotary_sw
            
            # Button pressed (level = 0)
            if level == 0:
                self.press_start_time[gpio] = current_time
                self.long_press_triggered[gpio] = False
                
                # For regular buttons, trigger press immediately
                if not is_rotary_switch and button_number:
                    if self.button_press_callback and self.loop:
                        logger.info(f"Button press detected on button {button_number}")
                        asyncio.run_coroutine_threadsafe(
                            self.button_press_callback(button_number), 
                            self.loop
                        )
                
                # Only start long press monitoring for rotary switch
                elif is_rotary_switch and self.loop:
                    task = asyncio.run_coroutine_threadsafe(
                        self._monitor_long_press(gpio, button_number),
                        self.loop
                    )
                    self.monitor_tasks[gpio] = task
            
            # Button released (level = 1) - only handle for rotary switch
            elif level == 1 and gpio in self.press_start_time and is_rotary_switch:
                duration = current_time - self.press_start_time[gpio]
                
                # Cancel monitoring task if exists
                if gpio in self.monitor_tasks:
                    self.monitor_tasks[gpio].cancel()
                    del self.monitor_tasks[gpio]
                
                # Handle rotary switch special functions
                if not self.long_press_triggered.get(gpio, False):
                    # Check for triple press
                    if gpio not in self.press_count:
                        self.press_count[gpio] = 0
                        self.last_press_time[gpio] = 0
                        
                    time_since_last = current_time - self.last_press_time[gpio]
                    if time_since_last < self.TRIPLE_PRESS_INTERVAL:
                        self.press_count[gpio] += 1
                        
                        if self.press_count[gpio] >= 2:  # Third press
                            if self.triple_press_callback and self.loop:
                                logger.info("Triple press detected on rotary switch")
                                asyncio.run_coroutine_threadsafe(
                                    self.triple_press_callback(button_number), 
                                    self.loop
                                )
                            self.press_count[gpio] = 0
                            self.last_press_time[gpio] = 0
                            return
                    else:
                        self.press_count[gpio] = 1
                    
                    self.last_press_time[gpio] = current_time
            
        except Exception as e:
            logger.error(f"Error in button handler: {e}", exc_info=True)

    async def _monitor_long_press(self, gpio, button_number):
        """Monitor button press duration and trigger long press when threshold is met."""
        try:
            while gpio in self.press_start_time:
                current_time = time.time()
                duration = current_time - self.press_start_time[gpio]
                
                # Check if button is still pressed and duration exceeds threshold
                if (duration >= self.LONG_PRESS_DURATION and 
                    not self.long_press_triggered.get(gpio, False)):
                    if self.long_press_callback:
                        logger.info(f"Long press detected for button {button_number}")
                        self.long_press_triggered[gpio] = True
                        self.press_count[gpio] = 0  # Reset press count
                        await self.long_press_callback(button_number)
                    break
                
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