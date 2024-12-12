"""
Test suite for API routes.
Tests HTTP endpoints and basic WebSocket connectivity.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket
from src.api.main import app
import asyncio

@pytest.mark.asyncio
async def test_websocket_endpoint():
    """Test that WebSocket endpoint exists and accepts connections"""
    client = TestClient(app)
    with client.websocket_connect("/ws") as websocket:
        websocket.send_json({"type": "ping"})
        response = websocket.receive_json()
        assert response["type"] == "pong"

@pytest.mark.asyncio
async def test_station_configuration():
    """Test station configuration API"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/stations/", json={
            "name": "Test Radio",
            "url": "http://test.com/stream",
            "slot": 1
        })
        assert response.status_code == 200