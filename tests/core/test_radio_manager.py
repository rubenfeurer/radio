import pytest
from src.core.radio_manager import RadioManager
from src.core.models import RadioStation, SystemStatus
from unittest.mock import patch
import json
from unittest.mock import mock_open

@pytest.fixture
def radio_manager():
    return RadioManager()

@pytest.fixture
def mock_settings(monkeypatch):
    """Mock settings for testing"""
    test_settings = {
        1: "Test Station 1",
        2: "Test Station 2",
        3: "Test Station 3"
    }
    monkeypatch.setattr('config.config.settings.DEFAULT_STATIONS', test_settings)
    return test_settings

@pytest.mark.asyncio
async def test_radio_manager_loads_configured_stations(mock_settings):
    # Mock the stations.json data
    mock_stations = [
        {"name": "Test Station 1", "url": "http://test1.com"},
        {"name": "Test Station 2", "url": "http://test2.com"},
        {"name": "Test Station 3", "url": "http://test3.com"}
    ]
    
    with patch('builtins.open', mock_open(read_data=json.dumps(mock_stations))):
        manager = RadioManager()
        
        # Verify stations were loaded into correct slots
        for slot, name in mock_settings.items():
            station = manager.get_station(slot)
            assert station is not None
            assert station.name == name

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

@pytest.mark.asyncio
async def test_play_station(radio_manager):
    station = RadioStation(
        name="Test Radio",
        url="http://test.stream/radio",
        slot=1
    )
    radio_manager.add_station(station)
    await radio_manager.play_station(1)
    status = radio_manager.get_status()
    assert status.is_playing == True
    assert status.current_station == 1 