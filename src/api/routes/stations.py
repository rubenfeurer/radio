from fastapi import APIRouter, HTTPException
from src.core.models import RadioStation
from src.core.radio_manager import RadioManager

router = APIRouter()
radio_manager = RadioManager()

@router.post("/stations/")
async def add_station(station: RadioStation):
    """
    Add or update a radio station in a specific slot.
    
    - If the slot is empty, adds the new station
    - If the slot is occupied, replaces the existing station
    - Requires name, URL, and slot number
    
    Returns a success message when station is added/updated.
    """
    radio_manager.add_station(station)
    return {"message": "Station added successfully"}

@router.get("/stations/{slot}", response_model=RadioStation)
async def get_station(slot: int):
    """
    Retrieve information about a radio station in a specific slot.
    
    - Returns station details if found (name, URL, slot)
    - Returns 404 error if no station exists in the specified slot
    """
    station = radio_manager.get_station(slot)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    return station

@router.post("/stations/{slot}/play")
async def play_station(slot: int):
    """
    Start playing the radio station in the specified slot.
    
    - Automatically stops any currently playing station
    - Returns 404 error if no station exists in the specified slot
    - Returns success message when playback starts
    """
    station = radio_manager.get_station(slot)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    await radio_manager.play_station(slot)
    return {"message": "Playing station"}

@router.post("/stations/{slot}/toggle")
async def toggle_station(slot: int):
    """
    Toggle play/pause for the radio station in the specified slot.
    
    - If the station is currently playing: pauses it
    - If the station is currently paused: starts playing it
    - If another station is playing: stops it and plays this station
    - Returns 404 error if no station exists in the specified slot
    
    Returns the current play state (playing/paused) after toggling.
    """
    try:
        result = await radio_manager.toggle_station(slot)
        return {
            "message": f"Station in slot {slot} {'playing' if result else 'paused'}",
            "status": "playing" if result else "paused"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) 