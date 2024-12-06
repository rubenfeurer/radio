from pydantic import BaseModel
from typing import Optional, Dict

class Settings(BaseModel):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Internet Radio"
    
    # Default Station Settings
    DEFAULT_STATIONS: Dict[int, str] = {
        1: "GDS.FM",        # Station for Button 1
        2: "Radio Swiss Jazz",  # Station for Button 2
        3: "SRF 1"           # Station for Button 3
    }
    
    # Hardware Settings - Push Buttons
    BUTTON_PIN_1: int = 17  # GPIO17 (Pin 11)
    BUTTON_PIN_2: int = 16  # GPIO16 (Pin 36)
    BUTTON_PIN_3: int = 26  # GPIO26 (Pin 37)
    
    # Hardware Settings - Rotary Encoder
    ROTARY_CLK: int = 11    # GPIO11 (Pin 23)
    ROTARY_DT: int = 9      # GPIO9  (Pin 21)
    ROTARY_SW: int = 10     # GPIO10 (Pin 19)
    ROTARY_CLOCKWISE_INCREASES: bool = True  # True = clockwise increases volume
    
    # Audio Settings
    DEFAULT_VOLUME: int = 70
    
    # Rotary Encoder Sensitivity
    ROTARY_VOLUME_STEP: int = 5  # Default step size for volume change
    
    # Button press durations (in seconds)
    LONG_PRESS_DURATION: float = 3.0
    DOUBLE_PRESS_INTERVAL: float = 0.5
    
    model_config = {
        "case_sensitive": True
    }

settings = Settings() 