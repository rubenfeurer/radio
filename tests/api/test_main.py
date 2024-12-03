import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.core.models import RadioStation, SystemStatus

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "status": "online", 
        "message": "Internet Radio API is running"
    }

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_websocket():
    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "status_request"})
        data = websocket.receive_json()
        assert data["type"] == "status_response"
        assert isinstance(data["data"], dict)

def test_add_station():
    station = RadioStation(name="Test Radio", url="http://test.stream/radio", slot=1)
    response = client.post("/stations/", json=station.model_dump())
    assert response.status_code == 200
    
def test_get_station():
    # First add a station
    station = RadioStation(name="Test Radio", url="http://test.stream/radio", slot=1)
    client.post("/stations/", json=station.model_dump())
    
    # Then get it
    response = client.get("/stations/1")
    assert response.status_code == 200
    assert RadioStation(**response.json()) == station
