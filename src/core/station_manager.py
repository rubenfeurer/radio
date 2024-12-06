from typing import Dict, Optional
from src.core.models import RadioStation
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class StationManager:
    """Single responsibility: Manage station loading, saving, and state"""
    
    STATIONS_FILE = Path("data/assigned_stations.json")
    
    def __init__(self):
        self._stations: Dict[int, RadioStation] = {}
        self._load_stations()
    
    def _load_stations(self) -> None:
        """Load stations with clear priority: assigned > default"""
        try:
            # First try assigned stations
            assigned = self._load_assigned_stations()
            self._stations.update(assigned)
            
            # Log what was loaded
            logger.info(f"Loaded {len(assigned)} assigned stations: {[s.name for s in assigned.values()]}")
            
            # Only load defaults for empty slots
            self._load_defaults_for_empty_slots()
            
        except Exception as e:
            logger.error(f"Error loading stations: {e}")
            raise
    
    def _load_assigned_stations(self) -> Dict[int, RadioStation]:
        """Load stations from JSON file"""
        if not self.STATIONS_FILE.exists():
            return {}
            
        with open(self.STATIONS_FILE, 'r') as f:
            data = json.load(f)
            return {
                int(slot): RadioStation(**station_data)
                for slot, station_data in data.items()
                if station_data is not None
            }
    
    def _load_defaults_for_empty_slots(self) -> None:
        """Load defaults only for slots that are empty"""
        from src.utils.station_loader import load_default_stations
        defaults = load_default_stations()
        
        for slot, station in defaults.items():
            if slot not in self._stations:
                self._stations[slot] = station
                logger.info(f"Added default station to empty slot {slot}: {station.name}")
    
    def save_station(self, station: RadioStation) -> None:
        """Save station to persistent storage and memory"""
        if station.slot is None:
            raise ValueError("Station must have a slot assigned")
            
        # Update memory
        self._stations[station.slot] = station
        
        # Update file
        self._save_to_file()
        logger.info(f"Saved station {station.name} to slot {station.slot}")
    
    def _save_to_file(self) -> None:
        """Save current stations to JSON file"""
        self.STATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            str(slot): {
                "name": station.name,
                "url": station.url,
                "slot": station.slot,
                "country": station.country,
                "location": station.location
            }
            for slot, station in self._stations.items()
        }
        
        with open(self.STATIONS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_station(self, slot: int) -> Optional[RadioStation]:
        """Get station by slot number"""
        return self._stations.get(slot)
    
    def get_all_stations(self) -> Dict[int, RadioStation]:
        """Get all loaded stations"""
        return self._stations.copy() 