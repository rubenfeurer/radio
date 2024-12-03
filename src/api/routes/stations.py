from fastapi import APIRouter, HTTPException
from src.core.models import RadioStation
from src.core.radio_manager import RadioManager

router = APIRouter()
radio_manager = RadioManager()

@router.post("/stations/")
async def add_station(station: RadioStation):
    radio_manager.add_station(station)
    return {"message": "Station added successfully"}

@router.get("/stations/{slot}", response_model=RadioStation)
async def get_station(slot: int):
    station = radio_manager.get_station(slot)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    return station

@router.post("/stations/{slot}/play")
async def play_station(slot: int):
    station = radio_manager.get_station(slot)
    if not station:
        raise HTTPException(status_code=404, detail="Station not found")
    await radio_manager.play_station(slot)
    return {"message": "Playing station"} 