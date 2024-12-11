import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from src.api.main import app
from src.core.models import WiFiStatus, WiFiNetwork

client = TestClient(app)

# Create mock data
mock_status = WiFiStatus(
    ssid="TestNetwork",
    signal_strength=70,
    is_connected=True,
    has_internet=True,
    available_networks=[
        WiFiNetwork(ssid="Network1", signal_strength=80, security="WPA2"),
        WiFiNetwork(ssid="Network2", signal_strength=60, security="WPA2")
    ]
)

@pytest.mark.asyncio
async def test_get_wifi_status(mock_wifi_manager_ap):
    """Test getting WiFi status"""
    mock_wifi_manager_ap.get_current_status.return_value = mock_status
    mock_wifi_manager_ap.get_preconfigured_ssid = MagicMock(return_value=None)
    
    with patch('src.api.routes.wifi.wifi_manager', mock_wifi_manager_ap):
        response = client.get("/api/v1/wifi/status")
        assert response.status_code == 200
        data = response.json()
        assert data["ssid"] == "TestNetwork"
        assert data["signal_strength"] == 70
        assert data["is_connected"] is True

@pytest.mark.asyncio
async def test_scan_networks(mock_wifi_manager_ap):
    """Test network scanning"""
    mock_wifi_manager_ap.get_current_status.return_value = mock_status
    mock_wifi_manager_ap.get_preconfigured_ssid = MagicMock(return_value=None)
    
    with patch('src.api.routes.wifi.wifi_manager', mock_wifi_manager_ap):
        response = client.get("/api/v1/wifi/status")
        assert response.status_code == 200
        data = response.json()
        assert data["ssid"] == "TestNetwork"
        assert len(data["available_networks"]) == 2

@pytest.mark.asyncio
async def test_connect_to_network(mock_wifi_manager_ap):
    """Test successful network connection"""
    # Create an awaitable mock that returns True
    async def mock_connect(*args, **kwargs):
        return True
    mock_wifi_manager_ap.connect_to_network.side_effect = mock_connect
    
    with patch('src.api.routes.wifi.wifi_manager', mock_wifi_manager_ap):
        response = client.post("/api/v1/wifi/connect",
            json={"ssid": "TestNetwork", "password": "TestPassword"})
        
        assert response.status_code == 200
        assert response.json() == {"status": "success"}
        mock_wifi_manager_ap.connect_to_network.assert_called_once_with(
            "TestNetwork", "TestPassword"
        )

@pytest.mark.asyncio
async def test_get_current_connection(mock_wifi_manager_ap):
    """Test getting current connection"""
    mock_wifi_manager_ap.get_current_status.return_value = mock_status
    
    with patch('src.api.routes.wifi.wifi_manager', mock_wifi_manager_ap):
        response = client.get("/api/v1/wifi/current")
        assert response.status_code == 200
        data = response.json()
        assert data["ssid"] == "TestNetwork"
        assert data["signal_strength"] == 70
        assert data["has_internet"] is True

@pytest.mark.asyncio
async def test_connect_invalid_request(mock_wifi_manager_ap):
    """Test connection with invalid request"""
    response = client.post("/api/v1/wifi/connect",
        json={"ssid": "", "password": ""})
    assert response.status_code == 400
    assert "detail" in response.json()

@pytest.mark.asyncio
async def test_connect_network_not_found(mock_wifi_manager_ap):
    """Test connection to non-existent network"""
    mock_wifi_manager_ap.connect_to_network.return_value = False
    
    with patch('src.api.routes.wifi.wifi_manager', mock_wifi_manager_ap):
        response = client.post("/api/v1/wifi/connect",
            json={"ssid": "NonExistentNetwork", "password": "TestPassword"})
        assert response.status_code == 400
        assert "detail" in response.json()

@pytest.mark.asyncio
async def test_forget_network(mock_wifi_manager_ap):
    """Test successful network removal"""
    mock_wifi_manager_ap._remove_connection.return_value = True
    
    with patch('src.api.routes.wifi.wifi_manager', mock_wifi_manager_ap):
        response = client.delete("/api/v1/wifi/forget/TestNetwork")
        assert response.status_code == 200
        assert response.json() == {"status": "success"}
        mock_wifi_manager_ap._remove_connection.assert_called_once_with("TestNetwork")

@pytest.mark.asyncio
async def test_forget_network_failure(mock_wifi_manager_ap):
    """Test failed network removal"""
    mock_wifi_manager_ap._remove_connection.return_value = False
    
    with patch('src.api.routes.wifi.wifi_manager', mock_wifi_manager_ap):
        response = client.delete("/api/v1/wifi/forget/TestNetwork")
        assert response.status_code == 400
        assert "detail" in response.json()