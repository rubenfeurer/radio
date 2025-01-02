from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict


class NetworkMode(str, Enum):
    AP = "AP"
    CLIENT = "CLIENT"


class Station(BaseModel):
    """Base station model"""

    name: str
    url: str
    slot: Optional[int] = None


class RadioStation(Station):
    """Extended station model with additional fields"""

    id: Optional[int] = None
    country: Optional[str] = None
    location: Optional[str] = None


class SystemStatus(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    current_station: Optional[int] = None
    volume: int = 70
    is_playing: bool = False


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
    available_networks: list[WiFiNetwork] = []
    preconfigured_ssid: Optional[str] = None


class ModeResponse(BaseModel):
    mode: NetworkMode
