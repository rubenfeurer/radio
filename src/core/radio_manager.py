from typing import Dict, Optional
from src.core.models import RadioStation, SystemStatus

class RadioManager:
    def __init__(self):
        self._stations: Dict[int, RadioStation] = {}
        self._status = SystemStatus()
        
    def add_station(self, station: RadioStation) -> None:
        if station.slot is not None:
            self._stations[station.slot] = station
            
    def remove_station(self, slot: int) -> None:
        if slot in self._stations:
            del self._stations[slot]
            if self._status.current_station == slot:
                self._status.current_station = None
                self._status.is_playing = False
                
    def get_station(self, slot: int) -> Optional[RadioStation]:
        return self._stations.get(slot)
        
    def play_station(self, slot: int) -> None:
        if slot in self._stations:
            self._status.current_station = slot
            self._status.is_playing = True
            # TODO: Implement actual playback using MPV
            
    def stop_playback(self) -> None:
        self._status.is_playing = False
        # TODO: Implement actual playback stop
        
    def get_status(self) -> SystemStatus:
        return self._status
        
    def set_volume(self, volume: int) -> None:
        self._status.volume = max(0, min(100, volume))
        # TODO: Implement actual volume control