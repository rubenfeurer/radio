"""
Test suite for API routes.
Tests HTTP endpoints and basic WebSocket connectivity.
"""

import pytest
from fastapi.testclient import TestClient
from src.api.main import app
import asyncio

client = TestClient(app)

def test_websocket_endpoint():
    """Test that WebSocket endpoint exists and accepts connections"""
    with client.websocket_connect("/ws") as websocket:
        # Send a ping and expect a pong
        websocket.send_json({"type": "ping"})
        response = websocket.receive_json()
        assert response["type"] == "pong"
        
        # Test complete - connection will close automatically

def test_station_configuration():
    """Test station configuration API"""
    response = client.post("/api/v1/stations/", json={
        "name": "Test Radio",
        "url": "http://test.com/stream",
        "slot": 1
    })
    assert response.status_code == 200