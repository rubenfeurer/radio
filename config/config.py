from pydantic import BaseModel
from typing import Optional, Dict
import socket
import json
import os

class Settings(BaseModel):
    # API Settings
    API_V1_STR: str = "/api/v1"
    WS_PATH: str = "/ws"
    API_PORT: int = 80
    DEV_PORT: int = 5173
    
    # API Path Settings
    API_PREFIX: str = "/api"  # New setting for the API prefix
    
    # Frontend paths
    FRONTEND_DEV_URL: str = f"http://{socket.gethostname()}.local:{DEV_PORT}"
    FRONTEND_BUILD_PATH: str = "web/build"
    
    # Network Settings
    HOSTNAME: str = socket.gethostname()  # Dynamically get system hostname
    AP_SSID: str = f"{HOSTNAME}"  # Use hostname as AP_SSID
    AP_PASSWORD: str = "radio@1234"
    AP_CHANNEL: int = 6
    AP_BAND: str = "bg"
    
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
    ROTARY_SW: int = 10     # GPIO10 (Pin 19)¨
    ROTARY_CLOCKWISE_INCREASES: bool = True  # True = clockwise increases volume
    
    # Audio Settings
    DEFAULT_VOLUME: int = 70
    
    # Rotary Encoder Sensitivity
    ROTARY_VOLUME_STEP: int = 5  # Default step size for volume change
    
    # Button press durations (in seconds)
    LONG_PRESS_DURATION: float = 3.0
    DOUBLE_PRESS_INTERVAL: float = 0.5
    
    def export_frontend_config(self) -> None:
        """Export relevant settings for frontend use"""
        frontend_config = {
            "API_V1_STR": self.API_V1_STR,
            "API_PREFIX": self.API_PREFIX,  # Add API prefix
            "WS_PATH": self.WS_PATH,
            "API_PORT": self.API_PORT,
            "DEV_PORT": self.DEV_PORT,
            "HOSTNAME": f"{self.HOSTNAME}.local"
        }
        
        # Write to a JSON file that can be imported by the frontend
        config_path = os.path.join("web", "src", "lib", "generated_config.json")
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, "w") as f:
            json.dump(frontend_config, f, indent=2)
            
        # Also generate a Vite config file
        vite_config = f"""
// This file is auto-generated from config.py - do not edit directly
export const DEV_PORT = {self.DEV_PORT}
export const API_PORT = {self.API_PORT}
export const API_V1_STR = "{self.API_V1_STR}"
export const API_PREFIX = "{self.API_PREFIX}"
export const WS_PATH = "{self.WS_PATH}"
export const HOSTNAME = "{self.HOSTNAME}.local"
"""
        with open(os.path.join("web", "src", "lib", "generated_config.js"), "w") as f:
            f.write(vite_config)

    model_config = {
        "case_sensitive": True
    }

settings = Settings()

# Export frontend configuration when this module is imported
settings.export_frontend_config() 