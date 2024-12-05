from pydantic import BaseModel
from typing import Optional

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