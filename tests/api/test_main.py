import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.core.models import RadioStation, SystemStatus
from src.api.models.requests import VolumeRequest, AssignStationRequest
from config.config import settings
from unittest.mock import MagicMock, patch

# Create test client
client = TestClient(app)

def test_root():
    """Test root API endpoint"""
    response = client.get(f"{settings.API_V1_STR}/")
    assert response.status_code == 200
    assert response.json() == {"message": "Radio API"}

def test_health():
    """Test health check endpoint"""
    response = client.get(f"{settings.API_V1_STR}/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

# Regular HTTP endpoint tests
def test_add_station():
    """Test adding a station"""
    station = RadioStation(
        name="Test Radio",
        url="http://test.stream/radio",
        slot=1
    )
    response = client.post(f"{settings.API_V1_STR}/stations/", json=station.model_dump())
    assert response.status_code == 200

def test_get_station():
    """Test getting a station"""
    # First add a station
    station = RadioStation(
        name="Test Radio",
        url="http://test.stream/radio",
        slot=1
    )
    client.post(f"{settings.API_V1_STR}/stations/", json=station.model_dump())
    
    # Then get it
    response = client.get(f"{settings.API_V1_STR}/stations/1")
    assert response.status_code == 200
    assert RadioStation(**response.json()) == station

def test_assign_station():
    """Test assigning a station to a slot"""
    request = AssignStationRequest(
        stationId=1,
        name="Test Station",
        url="http://test.stream/radio"
    )
    response = client.post(f"{settings.API_V1_STR}/stations/1/assign", json=request.model_dump())
    assert response.status_code == 200
    assert "success" in response.json()["status"]

def test_play_station():
    """Test playing a station"""
    # First add a station
    station = RadioStation(
        name="Test Radio",
        url="http://test.stream/radio",
        slot=1
    )
    client.post(f"{settings.API_V1_STR}/stations/", json=station.model_dump())
    
    # Then play it
    response = client.post(f"{settings.API_V1_STR}/stations/1/play")
    assert response.status_code == 200
    assert response.json() == {"message": "Playing station"}

def test_toggle_station():
    """Test toggling a station"""
    # First add a station
    station = RadioStation(
        name="Test Radio",
        url="http://test.stream/radio",
        slot=1
    )
    client.post(f"{settings.API_V1_STR}/stations/", json=station.model_dump())
    
    # Then toggle it
    response = client.post(f"{settings.API_V1_STR}/stations/1/toggle")
    assert response.status_code == 200
    assert "status" in response.json()
    assert "slot" in response.json()
