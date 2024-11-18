class GPIO:
    BCM = 11
    IN = 1
    OUT = 0
    FALLING = 2
    PUD_UP = 22
    
    @staticmethod
    def setmode(*args): pass
    
    @staticmethod
    def setup(*args, **kwargs): pass
    
    @staticmethod
    def add_event_detect(*args, **kwargs): pass
    
    @staticmethod
    def cleanup(): pass
    
    @staticmethod
    def output(*args): pass 