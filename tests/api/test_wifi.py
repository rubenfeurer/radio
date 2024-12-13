import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock, MagicMock
from src.api.main import app
from src.core.models import WiFiStatus, WiFiNetwork, ModeStatus, NetworkStatus
from src.core.mode_manager import NetworkMode

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

# Add mock data for mode tests
mock_network_status = NetworkStatus(
    wifi_status=mock_status,
    mode_status=ModeStatus(mode="client", is_switching=False)
)

@pytest.fixture
async def initialized_wifi_manager(wifi_manager):
    """Fixture to provide an initialized WiFiManager"""
    await wifi_manager.initialize()
    return wifi_manager

@pytest.mark.asyncio
async def test_get_wifi_status(initialized_wifi_manager):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/wifi/status")
    assert response.status_code == 200
    data = response.json()
    assert "ssid" in data
    assert "signal_strength" in data
    assert "is_connected" in data
    assert "has_internet" in data
    assert "available_networks" in data

@pytest.mark.asyncio
@patch('src.core.wifi_manager.WiFiManager.get_current_status')
async def test_scan_networks(mock_get_status):
    mock_get_status.return_value = mock_status
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/wifi/status")
    assert response.status_code == 200
    data = response.json()
    assert data["ssid"] == "TestNetwork"
    assert "signal_strength" in data
    assert "is_connected" in data
    assert "has_internet" in data
    assert "available_networks" in data

@pytest.mark.asyncio
@patch('src.core.wifi_manager.WiFiManager.connect_to_network')
async def test_connect_to_network(mock_connect):
    """Test successful network connection"""
    # Mock successful connection
    mock_connect.return_value = AsyncMock(return_value=True)()
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/wifi/connect",
            json={"ssid": "TestNetwork", "password": "TestPassword"})
    
    assert response.status_code == 200
    assert response.json() == {"status": "success"}
    
    # Verify mock was called with correct parameters
    mock_connect.assert_called_once_with("TestNetwork", "TestPassword")

@pytest.mark.asyncio
@patch('src.core.wifi_manager.WiFiManager.get_current_status')
async def test_get_current_connection(mock_get_status):
    mock_get_status.return_value = mock_status
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/wifi/status")
    assert response.status_code == 200
    data = response.json()
    assert data["ssid"] == "TestNetwork"

@pytest.mark.asyncio
@patch('src.core.wifi_manager.WiFiManager.connect_to_network')
async def test_connect_invalid_request(mock_connect):
    """Test connection with invalid request"""
    mock_connect.return_value = False
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/wifi/connect", json={
            "ssid": "",  # Invalid SSID
            "password": "test123"
        })
    assert response.status_code == 400

@pytest.mark.asyncio
@patch('src.core.wifi_manager.WiFiManager.connect_to_network')
async def test_connect_network_not_found(mock_connect):
    """Test connection to non-existent network"""
    mock_connect.return_value = False
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/wifi/connect", json={
            "ssid": "NonExistentNetwork",
            "password": "test123"
        })
    assert response.status_code == 400

@pytest.mark.asyncio
@patch('src.core.wifi_manager.WiFiManager._remove_connection')
async def test_forget_network(mock_remove):
    """Test successful network removal"""
    mock_remove.return_value = AsyncMock(return_value=True)()
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete("/api/v1/wifi/forget/TestNetwork")
    assert response.status_code == 200
    assert response.json() == {"status": "success"}
    
    # Verify mock was called with correct parameters
    mock_remove.assert_called_once_with("TestNetwork")

@pytest.mark.asyncio
@patch('src.core.wifi_manager.WiFiManager._remove_connection')
async def test_forget_network_failure(mock_remove):
    """Test failed network removal"""
    # Set up the mock to return False directly
    mock_remove.return_value = False
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.delete("/api/v1/wifi/forget/TestNetwork")
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Failed to remove network" in data["detail"]

# Add new test for debug_nmcli endpoint
@pytest.mark.asyncio
@patch('src.core.wifi_manager.WiFiManager._run_command')
async def test_debug_nmcli(mock_run_command):
    """Test debug_nmcli endpoint"""
    mock_run_command.side_effect = [
        MagicMock(
            stdout="Network1:80:WPA2:*\nNetwork2:70:WPA2:no",
            stderr="",
            returncode=0
        ),
        MagicMock(
            stdout="Network1:wifi:/etc/NetworkManager/system-connections/network1.nmconnection",
            stderr="",
            returncode=0
        )
    ]
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/wifi/debug_nmcli")
    assert response.status_code == 200
    data = response.json()
    assert "available_networks_output" in data

@pytest.mark.asyncio
@patch('src.core.mode_manager.ModeManager.detect_current_mode')
async def test_get_current_mode(mock_detect_mode):
    """Test getting current network mode"""
    mock_detect_mode.return_value = NetworkMode.CLIENT
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/wifi/mode")
    
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "client"
    assert "is_switching" in data
    assert isinstance(data["is_switching"], bool)

@pytest.mark.asyncio
@patch('src.core.mode_manager.ModeManager.switch_mode')
async def test_switch_mode_success(mock_switch):
    """Test successful mode switch"""
    mock_switch.return_value = True
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/wifi/mode/ap")
    
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert data["success"] is True

@pytest.mark.asyncio
@patch('src.core.mode_manager.ModeManager.switch_mode')
async def test_switch_mode_failure(mock_switch):
    """Test failed mode switch"""
    mock_switch.side_effect = Exception("Failed to switch mode")
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/wifi/mode/ap")
    
    assert response.status_code == 500
    data = response.json()
    assert "detail" in data

@pytest.mark.asyncio
async def test_switch_mode_invalid():
    """Test switch mode with invalid mode"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/wifi/mode/invalid")
    
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "Invalid mode" in data["detail"]

@pytest.mark.asyncio
@patch('src.core.mode_manager.ModeManager.detect_current_mode')
@patch('src.core.wifi_manager.WiFiManager.get_current_status')
async def test_get_network_status(mock_wifi_status, mock_detect_mode):
    """Test getting combined network status"""
    mock_wifi_status.return_value = mock_status
    mock_detect_mode.return_value = NetworkMode.CLIENT
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/wifi/network_status")
    
    assert response.status_code == 200
    data = response.json()
    assert "wifi_status" in data
    assert "mode_status" in data
    assert data["wifi_status"]["ssid"] == "TestNetwork"
    assert data["mode_status"]["mode"] == "client"

@pytest.mark.asyncio
async def test_websocket_mode_status():
    """Test WebSocket mode status updates"""
    from fastapi.testclient import TestClient
    
    client = TestClient(app)
    with client.websocket_connect("/api/v1/wifi/ws/mode") as websocket:
        data = websocket.receive_json()
        assert "type" in data
        assert data["type"] == "mode_status"
        assert "data" in data
        assert "mode" in data["data"]
        assert "is_switching" in data["data"]