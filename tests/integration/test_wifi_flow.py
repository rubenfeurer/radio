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
            available_networks=[]
        )
        
        # Make enable_ap_mode and disable_ap_mode async
        mock.enable_ap_mode = AsyncMock(return_value=True)
        mock.disable_ap_mode = AsyncMock(return_value=True)
        
        yield mock

def test_wifi_mode_switching_and_connection_flow(test_client, mock_wifi_manager):
    """Test the complete flow of switching between modes and connecting to networks"""
    
    # Test initial mode (should be DEFAULT)
    response = test_client.get("/api/v1/wifi/mode")
    assert response.status_code == 200
    assert response.json()["mode"] == "default"
    
    # Test switching to AP mode
    mock_wifi_manager.get_operation_mode.return_value = NetworkModeStatus(
        mode=NetworkMode.AP,
        ip_address="192.168.4.1"
    )
    
    response = test_client.post("/api/v1/wifi/mode/toggle")
    assert response.status_code == 200
    assert response.json()["mode"] == "ap"
    assert response.json()["ip_address"] == "192.168.4.1"
    
    # Test switching back to normal mode
    mock_wifi_manager.get_operation_mode.return_value = NetworkModeStatus(
        mode=NetworkMode.DEFAULT,
        ip_address="192.168.1.100"
    )
    
    response = test_client.post("/api/v1/wifi/mode/toggle")
    assert response.status_code == 200
    assert response.json()["mode"] == "default"
    assert response.json()["ip_address"] == "192.168.1.100"

def test_error_handling(test_client, mock_wifi_manager):
    """Test error scenarios"""
    
    # Test AP mode toggle failure
    mock_wifi_manager.enable_ap_mode.return_value = False
    mock_wifi_manager.get_operation_mode.return_value = NetworkModeStatus(
        mode=NetworkMode.DEFAULT,
        ip_address="192.168.1.100"
    )
    
    response = test_client.post("/api/v1/wifi/mode/toggle")
    assert response.status_code == 500
    assert "Failed to enable AP mode" in response.json()["detail"]
    
    # Test mode fetch failure
    mock_wifi_manager.get_operation_mode.side_effect = Exception("Failed to get mode")
    response = test_client.get("/api/v1/wifi/mode")
    assert response.status_code == 500
    assert "Failed to get mode" in response.json()["detail"]
    
    # Test network scan failure
    mock_wifi_manager.get_current_status.side_effect = Exception("Scan failed")
    response = test_client.get("/api/v1/wifi/status")
    # Status endpoint returns a default status object on error
    assert response.status_code == 200
    assert response.json() == {
        "ssid": None,
        "signal_strength": None,
        "is_connected": False,
        "has_internet": False,
        "available_networks": [],
        "preconfigured_ssid": None
    } 