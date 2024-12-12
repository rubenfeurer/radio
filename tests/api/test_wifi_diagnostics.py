import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from src.api.main import app
from src.core.models import WiFiStatus, WiFiNetwork

client = TestClient(app)

@pytest.mark.asyncio
@patch('src.core.wifi_manager.WiFiManager.get_current_status')
async def test_debug_wifi(mock_get_status):
    """Test debug endpoint returns WiFi status"""
    mock_status = WiFiStatus(
        ssid="TestNetwork",
        signal_strength=70,
        is_connected=True,
        has_internet=True,
        available_networks=[
            WiFiNetwork(ssid="Network1", signal_strength=80, security="WPA2")
        ]
    )
    mock_get_status.return_value = mock_status
    
    response = client.get("/api/v1/wifi/debug")
    assert response.status_code == 200
    data = response.json()
    assert data["ssid"] == "TestNetwork"
    assert data["is_connected"] is True

@pytest.mark.asyncio
@patch('src.core.wifi_manager.WiFiManager._run_command')
async def test_debug_nmcli(mock_run_command):
    """Test nmcli debug endpoint returns command output"""
    mock_run_command.side_effect = [
        MagicMock(
            returncode=0,
            stdout="Network1:80:WPA2:*\nNetwork2:70:WPA2:",
            stderr=""
        ),
        MagicMock(
            returncode=0,
            stdout="Network1:wifi:/etc/NetworkManager/system-connections/Network1",
            stderr=""
        )
    ]
    
    response = client.get("/api/v1/wifi/debug_nmcli")
    assert response.status_code == 200
    data = response.json()
    assert "available_networks_output" in data
    assert "saved_connections_output" in data
    assert "Network1" in data["available_networks_output"]
    assert "Network2" in data["available_networks_output"]

@pytest.mark.asyncio
@patch('src.core.wifi_manager.WiFiManager._run_command')
async def test_debug_nmcli_error(mock_run_command):
    """Test nmcli debug endpoint handles errors"""
    mock_run_command.side_effect = Exception("Command failed")
    
    response = client.get("/api/v1/wifi/debug_nmcli")
    assert response.status_code == 500
    assert "detail" in response.json() 