from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from enum import Enum

class NetworkMode(str, Enum):
    """Network operation mode"""
    AP = "ap"
    CLIENT = "client"

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
    signal_strength: int  # Percentage (0-100)
    security: Optional[str] = None
    in_use: bool = False
    saved: bool = False

    @classmethod
    def from_iw_scan(cls, ssid: str, signal_dbm: float, security: Optional[str] = None) -> 'WiFiNetwork':
        """Create WiFiNetwork instance from iw scan results"""
        # Convert dBm to percentage (typical range: -100 dBm to -50 dBm)
        if signal_dbm <= -100:
            signal_percent = 0
        elif signal_dbm >= -50:
            signal_percent = 100
        else:
            signal_percent = 2 * (signal_dbm + 100)
        
        return cls(
            ssid=ssid,
            signal_strength=int(signal_percent),
            security=security or "None"
        )

class WiFiStatus(BaseModel):
    """Model for WiFi connection status"""
    ssid: Optional[str] = None
    signal_strength: Optional[int] = None
    is_connected: bool = False
    has_internet: bool = False
    available_networks: List[WiFiNetwork] = []
    preconfigured_ssid: Optional[str] = None

class ModeStatus(BaseModel):
    """Model for network mode status"""
    mode: str
    is_switching: bool = False

class NetworkStatus(BaseModel):
    """Model for combined network status"""
    wifi_status: WiFiStatus
    mode_status: ModeStatus