import pytest
from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient
from src.api.main import app
from src.core.models import RadioStation
from src.api.models.requests import VolumeRequest, AssignStationRequest
import asyncio

# Add mock fixture for RadioManager
@pytest.fixture(autouse=True)
async def mock_radio_manager_singleton(monkeypatch, mock_radio_manager):
    """Mock the RadioManagerSingleton for all tests"""
    from src.core.singleton_manager import RadioManagerSingleton
    monkeypatch.setattr(RadioManagerSingleton, 'get_instance', lambda **kwargs: mock_radio_manager)

@pytest.mark.asyncio
async def test_root():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/")
        assert response.status_code == 200
        assert response.json() == {"message": "Radio API"}

@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

@pytest.mark.asyncio
async def test_websocket():
    """Test WebSocket connection and status request/response"""
    client = TestClient(app)
    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "status_request"})
        data = websocket.receive_json()
        assert data["type"] == "status_response"
        assert "data" in data
        assert isinstance(data["data"], dict)
        assert "volume" in data["data"]
        assert "is_playing" in data["data"]

@pytest.mark.asyncio
async def test_add_station():
    """Test adding a station"""
    station = RadioStation(
        name="Test Radio",
        url="http://test.stream/radio",
        slot=1
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/stations/", json=station.model_dump())
        assert response.status_code == 200
        assert response.json() == {"message": "Station added successfully"}

@pytest.mark.asyncio
async def test_get_station():
    """Test getting a station"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # First add a station
        station = RadioStation(
            name="Test Radio",
            url="http://test.stream/radio",
            slot=1
        )
        await client.post("/api/v1/stations/", json=station.model_dump())
        
        # Then get it
        response = await client.get("/api/v1/stations/1")
        assert response.status_code == 200
        assert RadioStation(**response.json()) == station

@pytest.mark.asyncio
async def test_assign_station():
    """Test assigning a station to a slot"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        request = AssignStationRequest(
            stationId=1,
            name="Test Station",
            url="http://test.stream/radio"
        )
        response = await client.post("/api/v1/stations/1/assign", json=request.model_dump())
        assert response.status_code == 200
        assert "success" in response.json()["status"]

@pytest.mark.asyncio
async def test_play_station():
    """Test playing a station"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # First add a station
        station = RadioStation(
            name="Test Radio",
            url="http://test.stream/radio",
            slot=1
        )
        await client.post("/api/v1/stations/", json=station.model_dump())
        
        # Then play it
        response = await client.post("/api/v1/stations/1/play")
        assert response.status_code == 200
        assert response.json() == {"message": "Playing station"}

@pytest.mark.asyncio
async def test_toggle_station():
    """Test toggling a station"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # First add a station
        station = RadioStation(
            name="Test Radio",
            url="http://test.stream/radio",
            slot=1
        )
        await client.post("/api/v1/stations/", json=station.model_dump())
        
        # Then toggle it
        response = await client.post("/api/v1/stations/1/toggle")
        assert response.status_code == 200
        assert "status" in response.json()
        assert "slot" in response.json()
