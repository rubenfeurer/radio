class MockPigpio:
    # GPIO modes
    INPUT = 0
    OUTPUT = 1
    ALT0 = 4
    ALT1 = 5
    ALT2 = 6
    ALT3 = 7
    ALT4 = 3
    ALT5 = 2
    
    # Pull up/down
    PUD_OFF = 0
    PUD_DOWN = 1
    PUD_UP = 2
    
    # Edge events
    RISING_EDGE = 0
    FALLING_EDGE = 1
    EITHER_EDGE = 2
    
    def __init__(self):
        self.connected = True
        self._callbacks = {}
    
    def set_mode(self, pin, mode):
        pass
    
    def set_pull_up_down(self, pin, pud):
        pass
    
    def callback(self, pin, edge, func):
        class MockCallback:
            def cancel(self):
                pass
        return MockCallback()
    
    def stop(self):
        self.connected = False
        
    def write(self, pin, value):
        pass
        
    def read(self, pin):
        return 0
        
    def set_watchdog(self, pin, timeout):
        pass
        
    def set_glitch_filter(self, pin, steady):
        pass
        
    def set_noise_filter(self, pin, steady, active):
        pass

def mock_pigpio_import():
    return MockPigpio() 