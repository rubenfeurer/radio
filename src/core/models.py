from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any

class RadioStation(BaseModel):
    name: str
    url: str
    slot: Optional[int] = None
    id: Optional[int] = None
    country: Optional[str] = None
    location: Optional[str] = None
    
class SystemStatus(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    current_station: Optional[Dict[str, Any]] = None
    volume: int = 70
    is_playing: bool = False

    def model_dump(self) -> Dict[str, Any]:
        """Custom serialization to handle nested objects"""
        return {
            "current_station": self.current_station,
            "volume": self.volume,
            "is_playing": self.is_playing
        }

class WiFiNetwork(BaseModel):
    """Model for available WiFi networks"""
    ssid: str
    signal_strength: int
    security: Optional[str] = None
    in_use: bool = False
    saved: bool = False

class WiFiStatus(BaseModel):
    """Model for WiFi connection status"""
    ssid: Optional[str] = None
    signal_strength: Optional[int] = None
    is_connected: bool = False
    has_internet: bool = False
    available_networks: List[WiFiNetwork] = []
    preconfigured_ssid: Optional[str] = None