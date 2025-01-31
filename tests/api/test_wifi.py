from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.core.models import WiFiNetwork, WiFiStatus

client = TestClient(app)

# Create mock data
mock_status = WiFiStatus(
    ssid="TestNetwork",
    signal_strength=70,
    is_connected=True,
    has_internet=True,
    available_networks=[
        WiFiNetwork(ssid="Network1", signal_strength=80, security="WPA2"),
        WiFiNetwork(ssid="Network2", signal_strength=60, security="WPA2"),
    ],
)


@patch("src.core.wifi_manager.WiFiManager.get_current_status")
def test_get_wifi_status(mock_get_status):
    mock_get_status.return_value = mock_status
    response = client.get("/api/v1/wifi/status")
    assert response.status_code == 200
    data = response.json()
    assert data["ssid"] == "TestNetwork"
    assert "signal_strength" in data
    assert "is_connected" in data
    assert "has_internet" in data
    assert "available_networks" in data


@patch("src.core.wifi_manager.WiFiManager.get_current_status")
def test_scan_networks(mock_get_status):
    mock_get_status.return_value = mock_status
    response = client.get("/api/v1/wifi/status")
    assert response.status_code == 200
    data = response.json()
    assert data["ssid"] == "TestNetwork"
    assert "signal_strength" in data
    assert "is_connected" in data
    assert "has_internet" in data
    assert "available_networks" in data


@pytest.mark.asyncio
@patch("src.core.wifi_manager.WiFiManager.connect_to_network")
async def test_connect_to_network(mock_connect):
    """Test successful network connection"""
    mock_connect.return_value = True

    response = client.post(
        "/api/v1/wifi/connect",
        json={"ssid": "TestNetwork", "password": "TestPassword"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "success"}
    mock_connect.assert_called_once_with("TestNetwork", "TestPassword")


@pytest.mark.asyncio
@patch("src.core.wifi_manager.WiFiManager.connect_to_network")
async def test_connect_invalid_request(mock_connect):
    """Test connection with invalid request"""
    mock_connect.return_value = False

    response = client.post("/api/v1/wifi/connect", json={"ssid": "", "password": ""})

    assert response.status_code == 400
    assert "detail" in response.json()


@pytest.mark.asyncio
@patch("src.core.wifi_manager.WiFiManager.connect_to_network")
async def test_connect_network_not_found(mock_connect):
    """Test connection to non-existent network"""
    mock_connect.return_value = False

    response = client.post(
        "/api/v1/wifi/connect",
        json={"ssid": "NonExistentNetwork", "password": "TestPassword"},
    )

    assert response.status_code == 400
    assert "detail" in response.json()


@pytest.mark.asyncio
@patch("src.core.wifi_manager.WiFiManager._remove_connection")
async def test_forget_network(mock_remove):
    """Test successful network removal"""
    mock_remove.return_value = True

    response = client.delete("/api/v1/wifi/forget/TestNetwork")
    assert response.status_code == 200
    assert response.json() == {"status": "success"}
    mock_remove.assert_called_once_with("TestNetwork")


@pytest.mark.asyncio
@patch("src.core.wifi_manager.WiFiManager._remove_connection")
async def test_forget_network_failure(mock_remove):
    """Test failed network removal"""
    mock_remove.return_value = False

    response = client.delete("/api/v1/wifi/forget/TestNetwork")
    assert response.status_code == 400
    assert "detail" in response.json()


@patch("src.core.wifi_manager.WiFiManager.get_current_status")
def test_get_current_connection(mock_get_status):
    mock_get_status.return_value = mock_status
    response = client.get("/api/v1/wifi/current")
    assert response.status_code == 200
    data = response.json()
    assert data["ssid"] == "TestNetwork"
    assert "signal_strength" in data
    assert "has_internet" in data
