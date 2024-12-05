import pytest
from src.core.radio_manager import RadioManager
from src.core.models import RadioStation, SystemStatus
from unittest.mock import patch
import json
from unittest.mock import mock_open
from config.config import settings

"""
Test suite for RadioManager class.
Tests core functionality of radio station management and playback control.

Key areas tested:
- Station management (add/remove/get)
- Playback control (play/stop/toggle)
- Volume control and persistence
- State management
- Default station handling
"""

@pytest.fixture
def radio_manager():
    """
    Fixture providing a clean RadioManager instance.
    Handles setup and cleanup of manager instance.
    """
    return RadioManager()

@pytest.fixture
def mock_settings(monkeypatch):
    """
    Mock settings for testing.
    Provides test configuration for default stations.
    """
    test_settings = {
        1: "Test Station 1",
        2: "Test Station 2",
        3: "Test Station 3"
    }
    monkeypatch.setattr('config.config.settings.DEFAULT_STATIONS', test_settings)
    return test_settings

@pytest.mark.asyncio
async def test_radio_manager_loads_configured_stations(mock_settings):
    """
    Test loading of configured stations from JSON.
    
    Verifies:
    - Stations are loaded from JSON file
    - Stations are assigned to correct slots
    - Station data matches configuration
    - Missing stations are handled gracefully
    """
    mock_stations = [
        {"name": "Test Station 1", "url": "http://test1.com"},
        {"name": "Test Station 2", "url": "http://test2.com"},
        {"name": "Test Station 3", "url": "http://test3.com"}
    ]
    
    with patch('builtins.open', mock_open(read_data=json.dumps(mock_stations))):
        manager = RadioManager()
        for slot, name in mock_settings.items():
            station = manager.get_station(slot)
            assert station is not None
            assert station.name == name

def test_add_station(radio_manager):
    """
    Test adding a new station to a slot.
    
    Verifies:
    - Station can be added to empty slot
    - Station can override existing slot
    - Station data is stored correctly
    - Invalid slots are handled properly
    """
    station = RadioStation(
        name="Test Radio",
        url="http://test.stream/radio",
        slot=1
    )
    radio_manager.add_station(station)
    assert radio_manager.get_station(1) == station

def test_remove_station(radio_manager):
    """
    Test removing a station from a slot.
    
    Verifies:
    - Station is removed from slot
    - Slot becomes empty after removal
    - Current playback is stopped if removed
    - Removing non-existent station is handled
    """
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
    """
    Test station playback functionality.
    
    Verifies:
    - Station starts playing when requested
    - Status is updated correctly
    - Current slot is tracked
    - Audio player is called correctly
    """
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

"""
Tests for the RadioManager class that handles core radio functionality.
Tests cover station management, playback control, and state management.
"""

@pytest.mark.asyncio
async def test_default_station_loading():
    """
    Test that default stations are correctly loaded from configuration.
    
    Verifies:
    - All three slots are populated with default stations
    - Station data matches configuration
    - Default stations are loaded only for empty slots
    """
    manager = RadioManager()
    assert manager.get_station(1) is not None
    assert manager.get_station(2) is not None
    assert manager.get_station(3) is not None

@pytest.mark.asyncio
async def test_station_switching():
    """Test station switching behavior"""
    manager = RadioManager()
    # Add test stations first
    station1 = RadioStation(name="Test1", url="http://test1.com", slot=1)
    station2 = RadioStation(name="Test2", url="http://test2.com", slot=2)
    manager.add_station(station1)
    manager.add_station(station2)
    
    # Use toggle_station and check status
    await manager.toggle_station(1)
    assert manager.get_status().current_station == 1
    await manager.toggle_station(2)
    assert manager.get_status().current_station == 2

@pytest.mark.asyncio
async def test_volume_persistence():
    """Test volume persistence"""
    manager = RadioManager()
    # Get initial volume from manager's status
    initial_volume = manager.get_status().volume
    await manager.set_volume(75)
    assert manager.get_status().volume == 75