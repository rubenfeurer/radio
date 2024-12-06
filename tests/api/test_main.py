import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.core.models import RadioStation
from src.api.models.requests import VolumeRequest, AssignStationRequest

# Add mock fixture for RadioManager
@pytest.fixture(autouse=True)
def mock_radio_manager_singleton(monkeypatch, mock_radio_manager):
    """Mock the RadioManagerSingleton for all tests"""
    from src.core.singleton_manager import RadioManagerSingleton
    monkeypatch.setattr(RadioManagerSingleton, 'get_instance', lambda **kwargs: mock_radio_manager)

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
    assert "frontend_url" in response.json()

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_websocket():
    """Test WebSocket connection and status request/response"""
    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "status_request"})
        data = websocket.receive_json()
        assert data["type"] == "status_response"
        assert isinstance(data["data"], dict)

def test_add_station():
    """Test adding a station"""
    station = RadioStation(
        name="Test Radio",
        url="http://test.stream/radio",
        slot=1
    )
    response = client.post("/api/v1/stations/", json=station.model_dump())
    assert response.status_code == 200
    assert response.json() == {"message": "Station added successfully"}

def test_get_station():
    """Test getting a station"""
    # First add a station
    station = RadioStation(
        name="Test Radio",
        url="http://test.stream/radio",
        slot=1
    )
    client.post("/api/v1/stations/", json=station.model_dump())
    
    # Then get it
    response = client.get("/api/v1/stations/1")
    assert response.status_code == 200
    assert RadioStation(**response.json()) == station

def test_assign_station():
    """Test assigning a station to a slot"""
    request = AssignStationRequest(
        stationId=1,
        name="Test Station",
        url="http://test.stream/radio"
    )
    response = client.post("/api/v1/stations/1/assign", json=request.model_dump())
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
    client.post("/api/v1/stations/", json=station.model_dump())
    
    # Then play it
    response = client.post("/api/v1/stations/1/play")
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
    client.post("/api/v1/stations/", json=station.model_dump())
    
    # Then toggle it
    response = client.post("/api/v1/stations/1/toggle")
    assert response.status_code == 200
    assert "status" in response.json()
    assert "slot" in response.json()
