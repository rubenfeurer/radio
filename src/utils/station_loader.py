import json
from typing import Dict
from src.core.models import RadioStation
from config.config import settings
import logging

logger = logging.getLogger(__name__)

def load_default_stations() -> Dict[int, RadioStation]:
    """
    Load default stations from stations.json based on names specified in config
    """
    try:
        # Load all stations from JSON
        with open('config/stations.json', 'r') as file:
            all_stations = json.load(file)
        
        # Create a name-to-station mapping
        station_map = {station['name']: station for station in all_stations}
        
        # Create RadioStation objects for configured defaults
        default_stations: Dict[int, RadioStation] = {}
        
        for slot, station_name in settings.DEFAULT_STATIONS.items():
            if station_name in station_map:
                station_data = station_map[station_name]
                default_stations[slot] = RadioStation(
                    name=station_data['name'],
                    url=station_data['url'],
                    slot=slot
                )
                logger.info(f"Loaded default station for slot {slot}: {station_name}")
            else:
                logger.warning(f"Station '{station_name}' not found in stations.json")
        
        return default_stations
    except Exception as e:
        logger.error(f"Error loading default stations: {str(e)}")
        return {} 