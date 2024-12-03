from pydantic import BaseModel
from typing import Optional

class RadioStation(BaseModel):
    id: Optional[int] = None
    name: str
    url: str
    slot: Optional[int] = None
    
class SystemStatus(BaseModel):
    current_station: Optional[int] = None
    volume: int = 70
    is_playing: bool = False 