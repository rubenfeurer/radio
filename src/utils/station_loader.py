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

def load_all_stations() -> Dict[int, RadioStation]:
    """Load all available radio stations from stations.json."""
    try:
        with open('config/stations.json', 'r') as f:
            stations_data = json.load(f)
            logger.info(f"Successfully loaded {len(stations_data)} stations from config/stations.json")
            
            # Convert the list of stations to RadioStation objects with auto-generated IDs
            stations_dict = {}
            for index, station in enumerate(stations_data, start=1):
                # Add an id field to each station
                station_with_id = {
                    'id': index,
                    **station  # Spread the rest of the station data
                }
                stations_dict[index] = RadioStation(**station_with_id)
            
            return stations_dict
    except Exception as e:
        logger.error(f"Error loading stations from config/stations.json: {str(e)}")
        return {} 