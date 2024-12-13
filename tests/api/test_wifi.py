import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock, MagicMock, PropertyMock
from src.api.main import app
from src.core.models import WiFiStatus, WiFiNetwork, ModeStatus, NetworkStatus
from src.core.mode_manager import NetworkMode
from starlette.websockets import WebSocketDisconnect
from fastapi.testclient import TestClient
import asyncio
import subprocess

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

@pytest.fixture
def mock_connect():
    """Fixture to provide a mock for connect_to_network"""
    with patch('src.core.wifi_manager.WiFiManager.connect_to_network') as mock:
        yield mock

@pytest.mark.asyncio
async def test_connect_to_network(mock_connect):
    """Test successful network connection"""
    # Set up AsyncMock correctly
    mock_connect.return_value = True  # AsyncMock will handle the awaiting
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/wifi/connect",
            json={"ssid": "TestNetwork", "password": "TestPassword"})
    
    assert response.status_code == 200
    assert response.json() == {"status": "success"}
    
    # Verify mock was called with correct parameters
    mock_connect.assert_called_once_with("TestNetwork", "TestPassword")

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
    
    # Verify WiFi status
    wifi_status = data["wifi_status"]
    assert wifi_status["ssid"] == "TestNetwork"
    assert wifi_status["signal_strength"] == 70
    assert wifi_status["is_connected"] is True
    assert wifi_status["has_internet"] is True
    assert len(wifi_status["available_networks"]) == 2
    
    # Verify mode status
    mode_status = data["mode_status"]
    assert mode_status["mode"] == "client"
    assert "is_switching" in mode_status
    assert isinstance(mode_status["is_switching"], bool)

@pytest.mark.asyncio
async def test_websocket_mode_status_normal():
    """Test WebSocket mode status updates in normal mode"""
    with patch('src.core.mode_manager.ModeManager.is_temp_mode', new_callable=PropertyMock) as mock_temp_mode, \
         patch('src.core.mode_manager.ModeManager.detect_current_mode', AsyncMock(return_value=NetworkMode.CLIENT)):
        mock_temp_mode.return_value = False
        
        client = TestClient(app)
        with client.websocket_connect("/api/v1/wifi/ws/mode") as websocket:
            data = websocket.receive_json()
            assert "type" in data
            assert data["type"] == "mode_status"
            assert "data" in data
            assert "mode" in data["data"]
            assert "is_switching" in data["data"]
            assert "is_temp_mode" in data["data"]
            assert data["data"]["mode"] == "client"
            assert isinstance(data["data"]["is_switching"], bool)
            assert data["data"]["is_temp_mode"] is False

@pytest.mark.asyncio
async def test_websocket_mode_status_scanning():
    """Test WebSocket mode status updates during scanning"""
    with patch('src.core.mode_manager.ModeManager.is_temp_mode', new_callable=PropertyMock) as mock_temp_mode, \
         patch('src.core.mode_manager.ModeManager.is_switching', new_callable=PropertyMock) as mock_switching, \
         patch('src.core.mode_manager.ModeManager.current_mode', new_callable=PropertyMock) as mock_current_mode:
        
        mock_temp_mode.return_value = True
        mock_switching.return_value = True
        mock_current_mode.return_value = NetworkMode.AP
        
        client = TestClient(app)
        with client.websocket_connect("/api/v1/wifi/ws/mode") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "mode_status"
            assert data["data"]["is_temp_mode"] is True
            assert data["data"]["is_switching"] is True
            assert data["data"]["mode"] == "ap"

@pytest.mark.asyncio
async def test_websocket_mode_status_disconnect_handling():
    """Test WebSocket disconnection handling"""
    client = TestClient(app)
    
    with client.websocket_connect("/api/v1/wifi/ws/mode") as websocket:
        # Get initial data
        data = websocket.receive_json()
        assert data["type"] == "mode_status"
        
        # Force disconnect
        websocket.close()
        
        # Attempting to receive after close should raise WebSocketDisconnect
        with pytest.raises(WebSocketDisconnect):
            websocket.receive_json()

@pytest.mark.asyncio
async def test_websocket_mode_status_error_handling():
    """Test WebSocket error handling"""
    with patch('src.core.mode_manager.ModeManager.detect_current_mode') as mock_detect:
        mock_detect.side_effect = Exception("Test error")
        
        client = TestClient(app)
        with client.websocket_connect("/api/v1/wifi/ws/mode") as websocket:
            data = websocket.receive_json()
            assert "error" in data
            assert "Test error" in str(data["error"])

@pytest.mark.asyncio
async def test_wifi_mode_switch_and_connect_flow():
    """Test the complete flow of switching to AP mode, scanning, and connecting"""
    
    mock_networks = [
        {
            "ssid": "SavedNetwork",
            "security": "WPA2",
            "signal_strength": 80,
            "saved": True,
            "in_use": False
        },
        {
            "ssid": "OtherNetwork",
            "security": "WPA2",
            "signal_strength": 70,
            "saved": False,
            "in_use": False
        }
    ]
    
    # Create mock iw scan output that matches the format in routes/wifi.py
    mock_iw_output = """
BSS 00:11:22:33:44:55
    signal: -20.00 dBm
    SSID: SavedNetwork
    WPA2: yes
BSS 66:77:88:99:aa:bb
    signal: -30.00 dBm
    SSID: OtherNetwork
    WPA2: yes
"""
    
    mock_wifi_status = WiFiStatus(
        ssid="SavedNetwork",
        signal_strength=80,
        is_connected=True,
        has_internet=True,
        available_networks=[WiFiNetwork(**n) for n in mock_networks]
    )
    
    # Create mock command results
    mock_command_result = type('CommandResult', (), {
        'stdout': mock_iw_output,
        'stderr': '',
        'returncode': 0
    })()
    
    async_get_status = AsyncMock(return_value=mock_wifi_status)
    async_connect = AsyncMock(return_value=True)
    async_switch_mode = AsyncMock(return_value=True)
    async_detect_mode = AsyncMock(side_effect=[NetworkMode.CLIENT, NetworkMode.AP, NetworkMode.AP])
    async_run_command = AsyncMock(return_value=mock_command_result)
    
    with patch('src.core.mode_manager.ModeManager.switch_mode', async_switch_mode), \
         patch('src.core.mode_manager.ModeManager.detect_current_mode', async_detect_mode), \
         patch('src.core.wifi_manager.WiFiManager.connect_to_network', async_connect), \
         patch('src.api.routes.wifi.mode_manager') as mock_mode_manager, \
         patch('src.core.wifi_manager.WiFiManager.get_current_status', async_get_status), \
         patch('src.api.routes.wifi.wifi_manager') as mock_wifi_manager, \
         patch('src.core.wifi_manager.WiFiManager._run_command', async_run_command), \
         patch('src.core.mode_manager.ModeManager._run_command', async_run_command):
        
        # Set up mock mode manager
        mock_mode_manager.detect_current_mode = async_detect_mode
        mock_mode_manager.switch_mode = async_switch_mode
        mock_mode_manager.is_temp_mode = False
        mock_mode_manager.is_switching = False
        mock_mode_manager.current_mode = NetworkMode.AP
        mock_mode_manager._run_command = async_run_command
        
        # Set up mock wifi manager
        mock_wifi_manager.get_current_status = async_get_status
        mock_wifi_manager.connect_to_network = async_connect
        mock_wifi_manager._run_command = async_run_command
        
        client = TestClient(app)
        
        # Test flow
        response = client.get("/api/v1/wifi/mode")
        assert response.status_code == 200
        assert response.json()["mode"] == "client"
        
        response = client.post("/api/v1/wifi/mode/ap")
        assert response.status_code == 200
        assert response.json()["success"] is True
        
        response = client.get("/api/v1/wifi/mode")
        assert response.status_code == 200
        assert response.json()["mode"] == "ap"
        
        # Test network scan
        response = client.post("/api/v1/wifi/scan")
        assert response.status_code == 200
        data = response.json()
        assert "networks" in data
        assert len(data["networks"]) == 2

@pytest.mark.asyncio
async def test_ap_mode_connect_success():
    """Test successful connection from AP mode"""
    # Mock mode manager responses
    async_temp_switch = AsyncMock(return_value=True)
    async_restore = AsyncMock(return_value=True)
    
    # Mock network scan results
    mock_status = WiFiStatus(
        ssid="",
        signal_strength=0,
        is_connected=False,
        has_internet=False,
        available_networks=[
            WiFiNetwork(ssid="TestNetwork", signal_strength=70, security="WPA2", saved=False, in_use=False)
        ]
    )
    async_get_status = AsyncMock(return_value=mock_status)
    async_connect = AsyncMock(return_value=True)
    async_get_preconfigured = AsyncMock(return_value=None)
    async_run_command = AsyncMock(return_value=MagicMock(returncode=0))
    
    with patch('src.core.mode_manager.ModeManager.temp_switch_to_client_mode', async_temp_switch), \
         patch('src.core.mode_manager.ModeManager.restore_previous_mode', async_restore), \
         patch('src.core.wifi_manager.WiFiManager.get_current_status', async_get_status), \
         patch('src.core.wifi_manager.WiFiManager.connect_to_network', async_connect), \
         patch('src.core.wifi_manager.WiFiManager._run_command', async_run_command), \
         patch('src.core.wifi_manager.WiFiManager.get_preconfigured_ssid', async_get_preconfigured):
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/wifi/ap/connect", 
                json={"ssid": "TestNetwork", "password": "TestPassword"})
        
        assert response.status_code == 200
        assert response.json() == {"status": "success"}
        
        # Verify correct sequence of calls
        async_temp_switch.assert_called_once()
        async_connect.assert_called_once_with("TestNetwork", "TestPassword")
        async_restore.assert_not_called()

@pytest.mark.asyncio
async def test_ap_mode_connect_failure():
    """Test failed connection from AP mode"""
    # Mock mode manager responses
    async_temp_switch = AsyncMock(return_value=True)
    async_restore = AsyncMock(return_value=True)
    
    # Mock network scan results
    mock_status = WiFiStatus(
        ssid="",
        signal_strength=0,
        is_connected=False,
        has_internet=False,
        available_networks=[
            WiFiNetwork(ssid="TestNetwork", signal_strength=70, security="WPA2", saved=False, in_use=False)
        ]
    )
    async_get_status = AsyncMock(return_value=mock_status)
    async_connect = AsyncMock(return_value=False)
    async_get_preconfigured = AsyncMock(return_value=None)
    async_run_command = AsyncMock(return_value=MagicMock(returncode=0))
    
    with patch('src.core.mode_manager.ModeManager.temp_switch_to_client_mode', async_temp_switch), \
         patch('src.core.mode_manager.ModeManager.restore_previous_mode', async_restore), \
         patch('src.core.wifi_manager.WiFiManager.get_current_status', async_get_status), \
         patch('src.core.wifi_manager.WiFiManager.connect_to_network', async_connect), \
         patch('src.core.wifi_manager.WiFiManager._run_command', async_run_command), \
         patch('src.core.wifi_manager.WiFiManager.get_preconfigured_ssid', async_get_preconfigured):
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/wifi/ap/connect",
                json={"ssid": "TestNetwork", "password": "TestPassword"})
        
        assert response.status_code == 400
        assert "Failed to connect to network" in response.json()["detail"]
        
        # Verify correct sequence of calls
        async_temp_switch.assert_called_once()
        async_connect.assert_called_once()
        assert async_restore.call_count == 2  # The mode is restored both after failed connection and in error handling

@pytest.mark.asyncio
async def test_ap_mode_connect_mode_switch_failure():
    """Test connection failure due to mode switch failure"""
    async_temp_switch = AsyncMock(return_value=False)
    async_connect = AsyncMock(return_value=True)
    async_restore = AsyncMock(return_value=True)
    
    with patch('src.core.mode_manager.ModeManager.temp_switch_to_client_mode', async_temp_switch), \
         patch('src.core.wifi_manager.WiFiManager.connect_to_network', async_connect), \
         patch('src.core.mode_manager.ModeManager.restore_previous_mode', async_restore):
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/wifi/ap/connect", 
                json={"ssid": "TestNetwork", "password": "TestPassword"})
            
        assert response.status_code == 400
        assert "Failed to switch to client mode" in response.json()["detail"]
        
        # Verify correct sequence of calls
        async_temp_switch.assert_called_once()
        async_connect.assert_not_called()  # Should not attempt connection
        async_restore.assert_not_called()  # No need to restore

@pytest.mark.asyncio
async def test_ap_mode_connect_exception_handling():
    """Test exception handling during AP mode connection"""
    async_temp_switch = AsyncMock(return_value=True)
    async_connect = AsyncMock(side_effect=Exception("Connection error"))
    async_restore = AsyncMock(return_value=True)
    
    # Mock network scan results
    mock_status = WiFiStatus(
        ssid="",
        signal_strength=0,
        is_connected=False,
        has_internet=False,
        available_networks=[
            WiFiNetwork(ssid="TestNetwork", signal_strength=70, security="WPA2", saved=False, in_use=False)
        ]
    )
    async_get_status = AsyncMock(return_value=mock_status)
    async_get_preconfigured = AsyncMock(return_value=None)
    async_run_command = AsyncMock(return_value=MagicMock(returncode=0))
    
    with patch('src.core.mode_manager.ModeManager.temp_switch_to_client_mode', async_temp_switch), \
         patch('src.core.mode_manager.ModeManager.restore_previous_mode', async_restore), \
         patch('src.core.wifi_manager.WiFiManager.get_current_status', async_get_status), \
         patch('src.core.wifi_manager.WiFiManager.connect_to_network', async_connect), \
         patch('src.core.wifi_manager.WiFiManager._run_command', async_run_command), \
         patch('src.core.wifi_manager.WiFiManager.get_preconfigured_ssid', async_get_preconfigured):
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/wifi/ap/connect",
                json={"ssid": "TestNetwork", "password": "TestPassword"})
        
        assert response.status_code == 400
        assert "Connection error" in response.json()["detail"]
        
        # Verify correct sequence of calls
        async_temp_switch.assert_called_once()
        async_connect.assert_called_once()
        assert async_restore.call_count == 1  # Changed from assert_called_once()

@pytest.mark.asyncio
async def test_ap_mode_scan():
    """Test network scanning in AP mode"""
    # Mock the mode detection to return AP mode
    mock_mode = AsyncMock(return_value=NetworkMode.AP)
    
    # Mock the iw scan command result with proper format
    mock_iw_scan = AsyncMock(return_value=subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout="""
BSS 00:11:22:33:44:55(on wlan0)
        signal: -50.00 dBm
        SSID: Network1
        WPA:     Version: 1
                Group cipher: CCMP
                Pairwise ciphers: CCMP
                Authentication suites: PSK
BSS 66:77:88:99:aa:bb(on wlan0)
        signal: -70.00 dBm
        SSID: Network2
        WPA:     Version: 1
                Group cipher: CCMP
                Pairwise ciphers: CCMP
                Authentication suites: PSK
""",
        stderr=""
    ))
    
    with patch('src.core.mode_manager.ModeManager.detect_current_mode', mock_mode), \
         patch('src.core.wifi_manager.WiFiManager._run_command', mock_iw_scan):
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/wifi/scan")
            
        assert response.status_code == 200
        data = response.json()
        assert "networks" in data
        assert len(data["networks"]) == 2
        
        # Check network details and order
        networks = data["networks"]
        assert networks[0]["ssid"] == "Network1"  # Stronger signal should be first
        assert networks[1]["ssid"] == "Network2"  # Weaker signal should be second
        
        # Check signal strength conversion (-50 dBm should be stronger than -70 dBm)
        assert networks[0]["signal_strength"] > networks[1]["signal_strength"]
        
        # Check security info
        assert networks[0]["security"] == "WPA2"
        assert networks[1]["security"] == "WPA2"
        
        # Verify the scan command was called
        mock_iw_scan.assert_called_with(
            ['sudo', 'iw', 'dev', 'wlan0', 'scan'],
            capture_output=True,
            text=True,
            timeout=10
        )

@pytest.mark.asyncio
async def test_client_mode_scan():
    """Test network scanning in CLIENT mode"""
    # Mock the mode detection to return CLIENT mode
    mock_mode = AsyncMock(return_value=NetworkMode.CLIENT)
    
    # Mock WiFiManager's get_current_status
    mock_status = AsyncMock(return_value=WiFiStatus(
        ssid="TestNetwork",
        signal_strength=70,
        is_connected=True,
        has_internet=True,
        available_networks=[
            WiFiNetwork(ssid="Network1", signal_strength=80, security="WPA2"),
            WiFiNetwork(ssid="Network2", signal_strength=60, security=None)
        ]
    ))
    
    with patch('src.core.mode_manager.ModeManager.detect_current_mode', mock_mode), \
         patch('src.core.wifi_manager.WiFiManager.get_current_status', mock_status):
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/wifi/scan")
            
        assert response.status_code == 200
        data = response.json()
        assert "networks" in data
        assert len(data["networks"]) == 2
        assert data["networks"][0]["ssid"] == "Network1"
        assert data["networks"][0]["security"] == "WPA2"
        assert data["networks"][1]["ssid"] == "Network2"
        assert data["networks"][1]["security"] is None
        
        # Verify the methods were called
        mock_mode.assert_called_once()
        mock_status.assert_called_once()

@pytest.mark.asyncio
async def test_ap_mode_connect_preconfigured():
    """Test connection to preconfigured network from AP mode"""
    async_temp_switch = AsyncMock(return_value=True)
    async_restore = AsyncMock(return_value=True)
    async_get_preconfigured = AsyncMock(return_value="Salt_5GHz_D8261F")
    async_run_command = AsyncMock(return_value=MagicMock(returncode=0, stdout="", stderr=""))
    
    with patch('src.core.mode_manager.ModeManager.temp_switch_to_client_mode', async_temp_switch), \
         patch('src.core.mode_manager.ModeManager.restore_previous_mode', async_restore), \
         patch('src.core.wifi_manager.WiFiManager.get_preconfigured_ssid', async_get_preconfigured), \
         patch('src.core.wifi_manager.WiFiManager._run_command', async_run_command):
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/wifi/ap/connect", 
                json={"ssid": "Salt_5GHz_D8261F", "password": "TestPassword"})
            
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        
        # Verify correct sequence of calls
        async_temp_switch.assert_called_once()
        async_get_preconfigured.assert_called_once()
        async_run_command.assert_called_with(['sudo', 'nmcli', 'connection', 'up', 'preconfigured'], 
            capture_output=True, text=True, timeout=30)
        async_restore.assert_not_called()  # Should not restore on success