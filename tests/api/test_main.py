import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from src.core.models import RadioStation, SystemStatus
from src.api.models.requests import VolumeRequest

client = TestClient(app)

def test_root():
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "http://radiod.local:5173"

def test_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_websocket():
    """Test WebSocket connection and status request/response"""
    with client.websocket_connect("/ws") as websocket:
        # Send a status request
        websocket.send_json({"type": "status_request"})
        
        # Get response
        data = websocket.receive_json()
        assert data["type"] == "status_response"
        assert isinstance(data["data"], dict)

def test_add_station():
    station = RadioStation(name="Test Radio", url="http://test.stream/radio", slot=1)
    response = client.post("/api/v1/stations/", json=station.model_dump())
    assert response.status_code == 200
    
def test_get_station():
    # First add a station
    station = RadioStation(name="Test Radio", url="http://test.stream/radio", slot=1)
    client.post("/api/v1/stations/", json=station.model_dump())
    
    # Then get it
    response = client.get("/api/v1/stations/1")
    assert response.status_code == 200
    assert RadioStation(**response.json()) == station

def test_get_volume():
    response = client.get("/api/v1/volume")
    assert response.status_code == 200
    assert "volume" in response.json()

def test_set_volume():
    new_volume = 50
    response = client.post("/api/v1/volume", json={"volume": new_volume})
    assert response.status_code == 200
    assert response.json() == {"message": "Volume set successfully"}

    # Verify the volume was set correctly
    response = client.get("/api/v1/volume")
    assert response.status_code == 200
    assert response.json()["volume"] == new_volume
