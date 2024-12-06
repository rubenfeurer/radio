from pydantic import BaseModel
from typing import Optional, List

class RadioStation(BaseModel):
    name: str
    url: str
    slot: Optional[int] = None
    id: Optional[int] = None
    country: Optional[str] = None
    location: Optional[str] = None
    
class SystemStatus(BaseModel):
    current_station: Optional[int] = None
    volume: int = 70
    is_playing: bool = False

class WiFiNetwork(BaseModel):
    """Model for available WiFi networks"""
    ssid: str
    signal_strength: int
    security: str
    in_use: bool = False

class WiFiStatus(BaseModel):
    """Model for WiFi connection status"""
    ssid: Optional[str] = None
    signal_strength: Optional[int] = None
    is_connected: bool = False
    has_internet: bool = False
    available_networks: List[WiFiNetwork] = []