from pydantic import BaseModel, Field

class VolumeRequest(BaseModel):
    volume: int = Field(..., ge=0, le=100) 