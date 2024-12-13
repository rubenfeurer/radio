import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from src.core.mode_manager import NetworkMode, mode_manager
from src.core.models import WiFiNetwork, WiFiStatus
from src.api.main import app

@pytest.mark.asyncio
async def test_wifi_mode_switch_and_connect_flow():
    """Test the complete flow of switching to AP mode, scanning, and connecting"""
    
    # Mock network data
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

    # Create mock WiFi status
    mock_wifi_status = WiFiStatus(
        ssid="SavedNetwork",
        signal_strength=80,
        is_connected=True,
        has_internet=True,
        available_networks=[
            WiFiNetwork(**mock_networks[0]),
            WiFiNetwork(**mock_networks[1])
        ]
    )

    # Create mock iw scan output
    mock_iw_output = """BSS 00:11:22:33:44:55
        signal: -20.00 dBm
        SSID: SavedNetwork
        WPA2: yes
    BSS 66:77:88:99:aa:bb
        signal: -30.00 dBm
        SSID: OtherNetwork
        WPA2: yes"""
    
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
         patch('src.api.routes.wifi.wifi_manager') as mock_wifi_manager:

        # Set up mock mode manager
        mock_mode_manager.detect_current_mode = async_detect_mode
        mock_mode_manager.switch_mode = async_switch_mode
        mock_mode_manager.is_temp_mode = False
        mock_mode_manager.is_switching = False
        mock_mode_manager.current_mode = NetworkMode.AP

        # Set up mock wifi manager
        mock_wifi_manager.get_current_status = async_get_status
        mock_wifi_manager.connect_to_network = async_connect
        mock_wifi_manager._run_command = async_run_command

        client = TestClient(app)

        # 1. Check initial mode (should be CLIENT)
        response = client.get("/api/v1/wifi/mode")
        assert response.status_code == 200
        assert response.json()["mode"] == "client"

        # 2. Switch to AP mode
        response = client.post("/api/v1/wifi/mode/ap")
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify mode switched to AP
        response = client.get("/api/v1/wifi/mode")
        assert response.status_code == 200
        assert response.json()["mode"] == "ap"

        # 3. Trigger network scan in AP mode
        response = client.post("/api/v1/wifi/scan")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert len(data["networks"]) == 2
        assert data["networks"][0]["ssid"] == "SavedNetwork"

        # 4. Connect to saved network
        response = client.post("/api/v1/wifi/connect", 
            json={"ssid": "SavedNetwork", "password": "testpass"})
        assert response.status_code == 200
        assert response.json()["status"] == "success"