from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.core.models import RadioStation
from src.core.singleton_manager import RadioManagerSingleton
from src.api.routes.websocket import broadcast_status_update
from src.utils.station_loader import load_all_stations
from typing import List, Optional
import logging

router = APIRouter()
radio_manager = RadioManagerSingleton.get_instance(status_update_callback=broadcast_status_update)
logger = logging.getLogger(__name__)

class AssignStationRequest(BaseModel):
    stationId: int
    name: str
    url: str
    country: Optional[str] = None
    location: Optional[str] = None

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
    """Toggle station playback"""
    try:
        if slot not in [1, 2, 3]:
            raise HTTPException(status_code=400, detail="Invalid slot number")
            
        is_playing = await radio_manager.toggle_station(slot)
        # RadioManager will broadcast status update via WebSocket
        return {
            "status": "playing" if is_playing else "stopped",
            "slot": slot
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stations", response_model=List[RadioStation])
async def get_all_stations():
    """Get a list of all available radio stations."""
    stations_dict = load_all_stations()
    # Convert dictionary to list for frontend consumption
    return list(stations_dict.values())

@router.post("/stations/{slot}/assign")
async def assign_station_to_slot(slot: int, request: AssignStationRequest):
    """Assign a station to a specific slot."""
    try:
        logger.info(f"Assigning station to slot {slot}. Request data: {request}")
        
        if slot not in [1, 2, 3]:
            raise HTTPException(status_code=400, detail="Invalid slot number")

        stations = load_all_stations()
        logger.debug(f"Available stations: {stations}")
        
        station = stations.get(request.stationId)
        if not station:
            logger.error(f"Station with ID {request.stationId} not found")
            raise HTTPException(status_code=404, detail=f"Station with ID {request.stationId} not found")
        
        # Create a new RadioStation instance with the slot number
        new_station = RadioStation(
            name=station.name,
            url=station.url,
            slot=slot,
            country=station.country,
            location=station.location
        )
        
        logger.info(f"Adding station to radio manager: {new_station}")
        radio_manager.add_station(new_station)
        
        return {
            "status": "success",
            "message": f"Station {station.name} assigned to slot {slot}"
        }
    except Exception as e:
        logger.error(f"Error assigning station: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))