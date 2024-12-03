from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Internet Radio"
    
    # Hardware Settings
    BUTTON_PIN_1: int = 17  # GPIO pin for button 1
    BUTTON_PIN_2: int = 27  # GPIO pin for button 2
    BUTTON_PIN_3: int = 22  # GPIO pin for button 3
    ROTARY_CLK: int = 5     # GPIO pin for rotary encoder CLK
    ROTARY_DT: int = 6      # GPIO pin for rotary encoder DT
    ROTARY_SW: int = 13     # GPIO pin for rotary encoder switch
    
    # Audio Settings
    DEFAULT_VOLUME: int = 70
    
    class Config:
        case_sensitive = True

settings = Settings() 