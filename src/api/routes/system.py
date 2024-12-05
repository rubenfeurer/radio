from fastapi import APIRouter, HTTPException
from src.api.models.requests import VolumeRequest
from src.core.singleton_manager import SingletonRadioManager
from src.api.routes.websocket import broadcast_status_update

router = APIRouter()

# Get the singleton instance
radio_manager = SingletonRadioManager.get_instance(status_update_callback=broadcast_status_update)

@router.get("/health")
async def health_check():
    """Check if the API is running and healthy."""
    return {"status": "healthy"}

@router.get("/volume")
async def get_volume():
    """Get the current volume level."""
    return {"volume": radio_manager.get_status().volume}

@router.post("/volume")
async def set_volume(request: VolumeRequest):
    """Set the system volume level."""
    if not 0 <= request.volume <= 100:
        raise HTTPException(status_code=400, detail="Volume must be between 0 and 100")
    
    await radio_manager.set_volume(request.volume)
    return {"message": "Volume set successfully"} 