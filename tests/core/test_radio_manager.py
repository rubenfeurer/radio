import pytest
from src.core.radio_manager import RadioManager
from src.core.models import RadioStation, SystemStatus

@pytest.fixture
def radio_manager():
    return RadioManager()

def test_add_station(radio_manager):
    station = RadioStation(
        name="Test Radio",
        url="http://test.stream/radio",
        slot=1
    )
    radio_manager.add_station(station)
    assert radio_manager.get_station(1) == station

def test_remove_station(radio_manager):
    station = RadioStation(
        name="Test Radio",
        url="http://test.stream/radio",
        slot=1
    )
    radio_manager.add_station(station)
    radio_manager.remove_station(1)
    assert radio_manager.get_station(1) is None

def test_play_station(radio_manager):
    station = RadioStation(
        name="Test Radio",
        url="http://test.stream/radio",
        slot=1
    )
    radio_manager.add_station(station)
    radio_manager.play_station(1)
    status = radio_manager.get_status()
    assert status.is_playing == True
    assert status.current_station == 1 