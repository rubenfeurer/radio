from fastapi import APIRouter
from src.api.models.requests import VolumeRequest
from src.core.radio_manager import RadioManager

router = APIRouter()
radio_manager = RadioManager()

@router.get("/health")
async def health_check():
    return {"status": "healthy"}

@router.get("/volume")
async def get_volume():
    return {"volume": radio_manager.get_status().volume}

@router.post("/volume")
async def set_volume(request: VolumeRequest):
    await radio_manager.set_volume(request.volume)
    return {"message": "Volume set successfully"} 