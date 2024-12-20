import pigpio
import time
from config.config import settings
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class RotaryTest:
    def __init__(self):
        self.pi = pigpio.pi()
        if not self.pi.connected:
            logger.error("Failed to connect to pigpio daemon")
            return
            
        # Get pins from settings
        self.rotary_clk = settings.ROTARY_CLK
        self.rotary_dt = settings.ROTARY_DT
        self.rotary_sw = settings.ROTARY_SW
        
        logger.info(f"Testing rotary encoder with pins:")
        logger.info(f"CLK: GPIO{self.rotary_clk}")
        logger.info(f"DT: GPIO{self.rotary_dt}")
        logger.info(f"SW: GPIO{self.rotary_sw}")
        
        # Setup pins
        for pin in [self.rotary_clk, self.rotary_dt, self.rotary_sw]:
            self.pi.set_mode(pin, pigpio.INPUT)
            self.pi.set_pull_up_down(pin, pigpio.PUD_UP)
            
        # Setup callbacks
        self.pi.callback(self.rotary_clk, pigpio.EITHER_EDGE, self._clk_callback)
        self.pi.callback(self.rotary_dt, pigpio.EITHER_EDGE, self._dt_callback)
        self.pi.callback(self.rotary_sw, pigpio.EITHER_EDGE, self._sw_callback)
        
        self.last_press_time = 0
        
    def _clk_callback(self, gpio, level, tick):
        logger.debug(f"CLK pin {gpio} changed to {level}")
        
    def _dt_callback(self, gpio, level, tick):
        logger.debug(f"DT pin {gpio} changed to {level}")
        
    def _sw_callback(self, gpio, level, tick):
        current_time = time.time()
        if level == 0:  # Button pressed
            self.last_press_time = current_time
            logger.info(f"Button pressed at {current_time}")
        elif level == 1 and self.last_press_time > 0:  # Button released
            duration = current_time - self.last_press_time
            logger.info(f"Button released. Press duration: {duration:.2f} seconds")
            if duration >= 3.0:
                logger.info("LONG PRESS DETECTED!")
                
    def run(self):
        logger.info("Starting rotary encoder test. Press Ctrl+C to exit.")
        logger.info("Try the following:")
        logger.info("1. Turn the encoder clockwise and counter-clockwise")
        logger.info("2. Press the button briefly (short press)")
        logger.info("3. Press and hold the button for >3 seconds (long press)")
        
        try:
            while True:
                # Print current state every second
                clk_state = self.pi.read(self.rotary_clk)
                dt_state = self.pi.read(self.rotary_dt)
                sw_state = self.pi.read(self.rotary_sw)
                logger.debug(f"Current states - CLK: {clk_state}, DT: {dt_state}, SW: {sw_state}")
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Test ended by user")
        finally:
            self.cleanup()
            
    def cleanup(self):
        if hasattr(self, 'pi') and self.pi.connected:
            self.pi.stop()
            logger.info("Cleaned up GPIO resources")

if __name__ == "__main__":
    test = RotaryTest()
    test.run() 