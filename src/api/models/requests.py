from pydantic import BaseModel
from typing import Optional

class VolumeRequest(BaseModel):
    volume: int

class AssignStationRequest(BaseModel):
    stationId: int
    name: str
    url: str
    country: Optional[str] = None
    location: Optional[str] = None 