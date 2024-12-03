from typing import Dict, Optional
from src.core.models import RadioStation, SystemStatus
from src.hardware.audio_player import AudioPlayer

class RadioManager:
    def __init__(self):
        self._stations: Dict[int, RadioStation] = {}
        self._status = SystemStatus()
        self._player = AudioPlayer()
        
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
        
    async def play_station(self, slot: int) -> None:
        if slot in self._stations:
            station = self._stations[slot]
            await self._player.play(station.url)
            self._status.current_station = slot
            self._status.is_playing = True
            
    async def stop_playback(self) -> None:
        await self._player.stop()
        self._status.is_playing = False
        
    def get_status(self) -> SystemStatus:
        return self._status
        
    async def set_volume(self, volume: int) -> None:
        await self._player.set_volume(volume)
        self._status.volume = volume