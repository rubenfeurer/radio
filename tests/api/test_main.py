import shutil
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from config.config import settings
from src.api.main import app
from src.api.models.requests import AssignStationRequest
from src.core.models import RadioStation

# Create test client
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Setup test environment before each test"""
    # Create a temporary directory
    test_dir = tempfile.mkdtemp()
    test_data_dir = Path(test_dir) / "data"
    test_data_dir.mkdir(exist_ok=True)

    # Create test stations file
    test_stations_file = test_data_dir / "assigned_stations.json"
    test_stations_file.touch()

    # Initialize empty JSON file
    with open(test_stations_file, "w") as f:
        f.write("{}")

    # Patch the STATIONS_FILE path in StationManager
    with patch(
        "src.core.station_manager.StationManager.STATIONS_FILE",
        test_stations_file,
    ):
        yield test_stations_file

    # Cleanup after test
    shutil.rmtree(test_dir)


@pytest.fixture
def mock_radio_manager():
    """Mock RadioManager for testing"""
    with patch("src.core.singleton_manager.RadioManagerSingleton.get_instance") as mock:
        manager = AsyncMock()
        manager.initialize = AsyncMock()
        mock.return_value = manager
        yield manager


@pytest.fixture
def test_client(mock_radio_manager):
    """Test client with mocked RadioManager"""
    with TestClient(app) as client:
        yield client


@pytest.mark.asyncio
async def test_root(test_client):
    """Test root API endpoint"""
    response = test_client.get(f"{settings.API_V1_STR}/")
    assert response.status_code == 200
    assert response.json() == {"message": "Radio API"}


@pytest.mark.asyncio
async def test_health():
    """Test health check endpoint"""
    response = client.get(f"{settings.API_V1_STR}/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_add_station():
    """Test adding a station"""
    station = RadioStation(name="Test Radio", url="http://test.stream/radio", slot=1)
    response = client.post(
        f"{settings.API_V1_STR}/stations/",
        json=station.model_dump(),
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_station():
    """Test getting a station"""
    # First add a station
    station = RadioStation(name="Test Radio", url="http://test.stream/radio", slot=1)
    client.post(f"{settings.API_V1_STR}/stations/", json=station.model_dump())

    # Then get it
    response = client.get(f"{settings.API_V1_STR}/stations/1")
    assert response.status_code == 200
    assert RadioStation(**response.json()) == station


@pytest.mark.asyncio
async def test_assign_station():
    """Test assigning a station to a slot"""
    request = AssignStationRequest(
        stationId=1,
        name="Test Station",
        url="http://test.stream/radio",
    )
    response = client.post(
        f"{settings.API_V1_STR}/stations/1/assign",
        json=request.model_dump(),
    )
    assert response.status_code == 200
    assert "success" in response.json()["status"]


@pytest.mark.asyncio
async def test_play_station():
    """Test playing a station"""
    # First add a station
    station = RadioStation(name="Test Radio", url="http://test.stream/radio", slot=1)
    client.post(f"{settings.API_V1_STR}/stations/", json=station.model_dump())

    # Then play it
    response = client.post(f"{settings.API_V1_STR}/stations/1/play")
    assert response.status_code == 200
    assert response.json() == {"message": "Playing station"}


@pytest.mark.asyncio
async def test_toggle_station():
    """Test toggling a station"""
    # First add a station
    station = RadioStation(name="Test Radio", url="http://test.stream/radio", slot=1)
    client.post(f"{settings.API_V1_STR}/stations/", json=station.model_dump())

    # Then toggle it
    response = client.post(f"{settings.API_V1_STR}/stations/1/toggle")
    assert response.status_code == 200
    assert "status" in response.json()
    assert "slot" in response.json()
