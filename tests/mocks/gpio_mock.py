class MockPigpio:
    def __init__(self):
        self.connected = True
    
    def set_mode(self, pin, mode):
        pass
    
    def set_pull_up_down(self, pin, pud):
        pass
    
    def callback(self, pin, edge, func):
        class MockCallback:
            def cancel(self):
                pass
        return MockCallback()

def mock_pigpio_import():
    return MockPigpio() 