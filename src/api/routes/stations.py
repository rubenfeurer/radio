from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.core.models import RadioStation
from src.core.singleton_manager import RadioManagerSingleton
from src.api.routes.websocket import broadcast_status_update
from src.utils.station_loader import load_all_stations, load_default_stations
from typing import List, Optional
import logging
import json
import os
from pathlib import Path

router = APIRouter(tags=["Radio Stations"])
radio_manager = RadioManagerSingleton.get_instance(status_update_callback=broadcast_status_update)
logger = logging.getLogger(__name__)

STATIONS_FILE = Path("data/assigned_stations.json")

def ensure_stations_file():
    """Ensure the stations file and directory exist"""
    STATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not STATIONS_FILE.exists():
        with open(STATIONS_FILE, "w") as f:
            json.dump({}, f)

def save_stations_to_file(slot: int, station: RadioStation):
    """Save station assignment to JSON file"""
    ensure_stations_file()
    try:
        # Load existing assignments
        with open(STATIONS_FILE, "r") as f:
            stations = json.load(f)
        
        # Update or add new station
        stations[str(slot)] = {
            "name": station.name,
            "url": station.url,
            "slot": slot,
            "country": station.country,
            "location": station.location
        }
        
        # Save back to file
        with open(STATIONS_FILE, "w") as f:
            json.dump(stations, f, indent=2)
            
    except Exception as e:
        logger.error(f"Error saving stations to file: {e}")
        raise

def load_stations_from_file():
    """Load station assignments from JSON file"""
    ensure_stations_file()
    try:
        with open(STATIONS_FILE, "r") as f:
            assigned_stations = json.load(f)
            
        # Check if we have any non-null stations
        has_valid_stations = any(
            station is not None 
            for station in assigned_stations.values()
        )
        
        if not has_valid_stations:
            # If all stations are null, load defaults
            logger.info("No valid stations in file, loading defaults")
            default_stations = load_default_stations()
            
            # Convert to the same format as assigned stations
            return {
                str(slot): {
                    "name": station.name,
                    "url": station.url,
                    "slot": slot,
                    "country": station.country,
                    "location": station.location
                }
                for slot, station in default_stations.items()
            }
            
        return assigned_stations
            
    except Exception as e:
        logger.error(f"Error loading stations from file: {e}")
        return {}

class AssignStationRequest(BaseModel):
    stationId: int
    name: str
    url: str
    country: Optional[str] = None
    location: Optional[str] = None

@router.post("/stations/", tags=["Station Management"])
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

@router.get("/stations/assigned", tags=["Station Management"])
async def get_assigned_stations():
    """Get all assigned stations from file, falling back to defaults if empty"""
    try:
        assigned_stations = load_stations_from_file()
        if not assigned_stations:
            logger.info("No assigned stations found, loading defaults")
            default_stations = load_default_stations()
            assigned_stations = {
                str(slot): {
                    "name": station.name,
                    "url": station.url,
                    "slot": slot,
                    "country": station.country,
                    "location": station.location
                }
                for slot, station in default_stations.items()
            }
        logger.debug(f"Returning stations: {assigned_stations}")
        return assigned_stations
    except Exception as e:
        logger.error(f"Error getting assigned stations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stations/{slot}", response_model=RadioStation, tags=["Station Info"])
async def get_station(slot: int):
    """
    Retrieve information about a radio station in a specific slot.
    First checks radio manager, then falls back to assigned stations file.
    """
    # First try to get station from radio manager
    station = radio_manager.get_station(slot)
    if station:
        return station
    
    # If not in radio manager, try assigned stations file
    assigned_stations = load_stations_from_file()
    if str(slot) in assigned_stations and assigned_stations[str(slot)]:
        return RadioStation(**assigned_stations[str(slot)])
    
    raise HTTPException(status_code=404, detail="Station not found")

@router.post("/stations/{slot}/play", tags=["Playback Control"])
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

@router.post("/stations/{slot}/toggle", tags=["Playback Control"])
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

@router.get("/stations", response_model=List[RadioStation], tags=["Station Info"])
async def get_all_stations():
    """Get a list of all available radio stations."""
    stations_dict = load_all_stations()
    # Convert dictionary to list for frontend consumption
    return list(stations_dict.values())

@router.post("/stations/{slot}/assign", tags=["Station Management"])
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
        
        # Save to JSON file
        save_stations_to_file(slot, new_station)
        
        return {
            "status": "success",
            "message": f"Station {station.name} assigned to slot {slot}"
        }
    except Exception as e:
        logger.error(f"Error assigning station: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))