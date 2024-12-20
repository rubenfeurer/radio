class MockPigpio:
    INPUT = 0
    OUTPUT = 1
    PUD_UP = 2
    PUD_DOWN = 3
    EITHER_EDGE = 4
    
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