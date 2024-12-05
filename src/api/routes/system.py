from fastapi import APIRouter, HTTPException
from src.api.models.requests import VolumeRequest
from src.core.radio_manager import RadioManager
from src.api.routes.websocket import broadcast_status_update

router = APIRouter()
radio_manager = RadioManager(status_update_callback=broadcast_status_update)

@router.get("/health")
async def health_check():
    """
    Check if the API is running and healthy.
    
    Returns a status indicating system health.
    """
    return {"status": "healthy"}

@router.get("/volume")
async def get_volume():
    """
    Get the current volume level.
    
    Returns an integer between 0 and 100 representing the current volume.
    """
    return {"volume": radio_manager.get_status().volume}

@router.post("/volume")
async def set_volume(request: VolumeRequest):
    """
    Set the system volume level.
    
    - Accepts a value between 0 and 100
    - 0 is muted
    - 100 is maximum volume
    
    Returns a success message when volume is set.
    """
    if not 0 <= request.volume <= 100:
        raise HTTPException(status_code=400, detail="Volume must be between 0 and 100")
    
    await radio_manager.set_volume(request.volume)
    return {"message": "Volume set successfully"} 