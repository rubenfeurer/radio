import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from src.api.main import app
from src.core.models import RadioStation, SystemStatus
from src.api.models.requests import VolumeRequest, AssignStationRequest
from config.config import settings
from unittest.mock import MagicMock, patch
import os
from pathlib import Path
import tempfile
import shutil

@pytest.fixture(autouse=True)
async def setup_test_environment(monkeypatch):
    """Setup test environment before each test"""
    # Create a temporary directory
    test_dir = tempfile.mkdtemp()
    test_data_dir = Path(test_dir) / "data"
    test_data_dir.mkdir(exist_ok=True)
    
    # Create test stations file
    test_stations_file = test_data_dir / "assigned_stations.json"
    test_stations_file.touch()
    
    # Initialize empty JSON file
    with open(test_stations_file, 'w') as f:
        f.write('{}')
    
    # Patch the STATIONS_FILE path in StationManager
    with patch('src.core.station_manager.StationManager.STATIONS_FILE', test_stations_file):
        yield test_stations_file
    
    # Cleanup after test
    shutil.rmtree(test_dir)

@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)

@pytest.fixture
async def async_client(client):
    """Create async client for testing"""
    async with AsyncClient(base_url="http://testserver") as ac:
        yield ac

@pytest.mark.asyncio
async def test_root(client):
    """Test root API endpoint"""
    response = client.get(f"{settings.API_V1_STR}/")
    assert response.status_code == 200
    assert response.json() == {"message": "Radio API"}

@pytest.mark.asyncio
async def test_health(client):
    """Test health check endpoint"""
    response = client.get(f"{settings.API_V1_STR}/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

@pytest.mark.asyncio
async def test_add_station(client):
    """Test adding a station"""
    station = RadioStation(
        name="Test Radio",
        url="http://test.stream/radio",
        slot=1
    )
    response = client.post(
        f"{settings.API_V1_STR}/stations/",
        json=station.model_dump()
    )
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_get_station(client):
    """Test getting a station"""
    station = RadioStation(
        name="Test Radio",
        url="http://test.stream/radio",
        slot=1
    )
    # Add station
    client.post(
        f"{settings.API_V1_STR}/stations/",
        json=station.model_dump()
    )
    # Get station
    response = client.get(f"{settings.API_V1_STR}/stations/1")
    assert response.status_code == 200
    assert RadioStation(**response.json()) == station

@pytest.mark.asyncio
async def test_assign_station(client):
    """Test assigning a station to a slot"""
    request = AssignStationRequest(
        stationId=1,
        name="Test Station",
        url="http://test.stream/radio"
    )
    response = client.post(
        f"{settings.API_V1_STR}/stations/1/assign",
        json=request.model_dump()
    )
    assert response.status_code == 200
    assert "success" in response.json()["status"]

@pytest.mark.asyncio
async def test_play_station(client):
    """Test playing a station"""
    station = RadioStation(
        name="Test Radio",
        url="http://test.stream/radio",
        slot=1
    )
    # Add station
    client.post(
        f"{settings.API_V1_STR}/stations/",
        json=station.model_dump()
    )
    # Play station
    response = client.post(f"{settings.API_V1_STR}/stations/1/play")
    assert response.status_code == 200
    assert response.json() == {"message": "Playing station"}

@pytest.mark.asyncio
async def test_toggle_station(client):
    """Test toggling a station"""
    station = RadioStation(
        name="Test Radio",
        url="http://test.stream/radio",
        slot=1
    )
    # Add station
    client.post(
        f"{settings.API_V1_STR}/stations/",
        json=station.model_dump()
    )
    # Toggle station
    response = client.post(f"{settings.API_V1_STR}/stations/1/toggle")
    assert response.status_code == 200
    assert "status" in response.json()
    assert "slot" in response.json()
