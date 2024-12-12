import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from src.api.main import app
from src.core.models import NetworkMode, NetworkModeStatus, WiFiNetwork, WiFiStatus

@pytest.fixture
def test_client():
    return TestClient(app)

@pytest.fixture
def mock_wifi_manager():
    with patch('src.api.routes.wifi.wifi_manager') as mock:
        # Setup default mock responses
        mock.get_operation_mode.return_value = NetworkModeStatus(
            mode=NetworkMode.DEFAULT,
            ip_address="192.168.1.100"
        )
        mock.get_current_status.return_value = WiFiStatus(
            ssid="TestNetwork",
            signal_strength=80,
            is_connected=True,
            has_internet=True,
            available_networks=[
                WiFiNetwork(
                    ssid="TestNetwork",
                    security="WPA2",
                    signal_strength=80,
                    in_use=True
                )
            ]
        )
        # Make async methods
        mock.connect_to_network = AsyncMock(return_value=True)
        mock.enable_ap_mode = AsyncMock(return_value=True)
        mock.disable_ap_mode = AsyncMock(return_value=True)
        yield mock

def test_wifi_mode_switching_and_connection_flow(test_client, mock_wifi_manager):
    """Test the complete flow"""
    
    # 1. Check initial mode
    response = test_client.get("/api/v1/wifi/mode")
    assert response.status_code == 200
    assert response.json()["mode"] == "default"
    
    # 2. Switch to AP mode
    mock_wifi_manager.get_operation_mode.return_value = NetworkModeStatus(
        mode=NetworkMode.AP,
        ip_address="192.168.4.1"
    )
    response = test_client.post("/api/v1/wifi/mode/toggle")
    assert response.status_code == 200
    assert response.json()["mode"] == "ap"
    
    # 3. Get available networks
    mock_wifi_manager.get_current_status.return_value = WiFiStatus(
        ssid=None,
        signal_strength=None,
        is_connected=False,
        has_internet=False,
        available_networks=[
            WiFiNetwork(
                ssid="HomeNetwork",
                security="WPA2",
                signal_strength=75,
                in_use=False
            )
        ]
    )
    response = test_client.get("/api/v1/wifi/networks")
    assert response.status_code == 200
    assert len(response.json()) == 1
    
    # 4. Connect to network
    mock_wifi_manager.connect_to_network.return_value = True
    response = test_client.post("/api/v1/wifi/connect", json={
        "ssid": "HomeNetwork",
        "password": "testpassword123"
    })
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_error_handling(test_client, mock_wifi_manager):
    """Test error scenarios"""
    
    # Test connection failure
    mock_wifi_manager.connect_to_network = AsyncMock(return_value=False)
    response = test_client.post("/api/v1/wifi/connect", json={
        "ssid": "NonExistentNetwork",
        "password": "wrongpassword"
    })
    assert response.status_code == 400
    
    # Test AP mode toggle failure
    mock_wifi_manager.enable_ap_mode = AsyncMock(side_effect=Exception("Failed to enable AP mode"))
    mock_wifi_manager.get_operation_mode.return_value = NetworkModeStatus(
        mode=NetworkMode.DEFAULT,
        ip_address="192.168.1.100"
    )
    response = test_client.post("/api/v1/wifi/mode/toggle")
    assert response.status_code == 500
    assert "Failed to enable AP mode" in response.json()["detail"]
    
    # Test network scan failure
    mock_wifi_manager.get_current_status.side_effect = Exception("Scan failed")
    response = test_client.get("/api/v1/wifi/networks")
    assert response.status_code == 500
    assert "Error getting networks" in response.json()["detail"] 