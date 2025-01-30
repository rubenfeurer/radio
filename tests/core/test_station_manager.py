import json
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from src.core.models import RadioStation
from src.core.station_manager import StationManager


@pytest.fixture
def station_manager():
    """Fixture providing a clean StationManager instance"""
    return StationManager()


@pytest.fixture
def test_stations():
    """Fixture providing test station data"""
    return {
        "1": {
            "name": "Test1",
            "url": "http://test1.com",
            "slot": 1,
            "country": "Test Country",
            "location": "Test Location",
        },
        "2": {
            "name": "Test2",
            "url": "http://test2.com",
            "slot": 2,
            "country": "Test Country",
            "location": "Test Location",
        },
    }


def test_load_assigned_stations(test_stations):
    """Test loading stations from JSON file"""
    with patch("builtins.open", mock_open(read_data=json.dumps(test_stations))):
        with patch.object(Path, "exists", return_value=True):
            manager = StationManager()
            stations = manager.get_all_stations()

            assert len(stations) == 2
            assert stations[1].name == "Test1"
            assert stations[2].name == "Test2"


def test_save_station(station_manager):
    """Test saving a station"""
    with patch("builtins.open", mock_open()) as mock_file:
        station = RadioStation(
            name="New Station",
            url="http://new.com",
            slot=1,
            country="Test",
            location="Test",
        )
        station_manager.save_station(station)

        # Verify file was written
        mock_file.assert_called_once()

        # Verify station was saved in memory
        saved_station = station_manager.get_station(1)
        assert saved_station == station


def test_empty_slots_get_defaults(station_manager):
    """Test that empty slots are filled with defaults"""
    # Mock both assigned stations file and default stations
    with patch("builtins.open", mock_open(read_data="{}")), patch.object(
        Path,
        "exists",
        return_value=True,
    ), patch("src.utils.station_loader.load_default_stations") as mock_defaults:

        # Create a new station manager with empty assigned stations
        station_manager = StationManager()

        # Setup mock default stations
        mock_defaults.return_value = {
            3: RadioStation(name="Default", url="http://default.com", slot=3),
        }

        # Force reload of stations to get defaults
        station_manager._load_stations()

        # Add a station to slot 1, leaving other slots empty
        station = RadioStation(name="Test", url="http://test.com", slot=1)
        station_manager.save_station(station)

        # Verify slot 3 got default station
        assert station_manager.get_station(3) is not None
        assert station_manager.get_station(3).name == "Default"


def test_assigned_stations_override_defaults(test_stations):
    """Test that assigned stations take precedence over defaults"""
    with patch("builtins.open", mock_open(read_data=json.dumps(test_stations))):
        with patch.object(Path, "exists", return_value=True):
            with patch(
                "src.utils.station_loader.load_default_stations",
            ) as mock_defaults:
                mock_defaults.return_value = {
                    1: RadioStation(name="Default1", url="http://default1.com", slot=1),
                }

                manager = StationManager()
                station = manager.get_station(1)

                assert station.name == "Test1"  # Assigned station, not default
