import pytest
from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient
from src.api.main import app
from src.core.models import RadioStation
from src.api.models.requests import VolumeRequest, AssignStationRequest
import asyncio
from src.core.mode_manager import NetworkMode
from unittest.mock import AsyncMock, MagicMock

# Add mock fixture for RadioManager
@pytest.fixture(autouse=True)
async def mock_radio_manager_singleton(monkeypatch, mock_radio_manager):
    """Mock the RadioManagerSingleton for all tests"""
    from src.core.singleton_manager import RadioManagerSingleton
    monkeypatch.setattr(RadioManagerSingleton, 'get_instance', lambda **kwargs: mock_radio_manager)

@pytest.fixture
async def mock_mode_manager(monkeypatch):
    """Mock mode manager to prevent actual system changes"""
    mock = MagicMock()
    mock.detect_current_mode = AsyncMock(return_value=NetworkMode.CLIENT)
    mock.switch_mode = AsyncMock(return_value=True)
    mock.is_switching = False
    
    # Patch the mode_manager in the wifi routes
    monkeypatch.setattr("src.api.routes.wifi.mode_manager", mock)
    return mock

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

@pytest.mark.asyncio
async def test_get_wifi_mode(mock_mode_manager):
    """Test getting current WiFi mode"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/wifi/mode")
        assert response.status_code == 200
        data = response.json()
        assert "mode" in data
        assert data["mode"] == "client"
        assert "is_switching" in data
        assert data["is_switching"] is False

@pytest.mark.asyncio
async def test_switch_wifi_mode(mock_mode_manager):
    """Test switching WiFi mode without actual system changes"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Test with uppercase mode
        response = await client.post("/api/v1/wifi/mode/AP")
        print(f"Response status: {response.status_code}")
        print(f"Response body: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert data["success"] is True
        mock_mode_manager.switch_mode.assert_called_once_with(NetworkMode.AP)

        # Reset mock for next test
        mock_mode_manager.switch_mode.reset_mock()

        # Test with lowercase mode
        response = await client.post("/api/v1/wifi/mode/ap")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
