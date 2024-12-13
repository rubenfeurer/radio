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

    # Create async mock for get_current_status
    async_get_status = AsyncMock(return_value=mock_wifi_status)
    async_connect = AsyncMock(return_value=True)
    async_switch_mode = AsyncMock(return_value=True)
    async_detect_mode = AsyncMock(side_effect=[NetworkMode.CLIENT, NetworkMode.AP, NetworkMode.AP])
    async_scan = AsyncMock(return_value=mock_networks)

    with patch('src.core.mode_manager.ModeManager.switch_mode', async_switch_mode), \
         patch('src.core.mode_manager.ModeManager.detect_current_mode', async_detect_mode), \
         patch('src.core.mode_manager.ModeManager.scan_from_ap_mode', async_scan), \
         patch('src.core.wifi_manager.WiFiManager.connect_to_network', async_connect), \
         patch('src.api.routes.wifi.mode_manager') as mock_mode_manager, \
         patch('src.core.wifi_manager.WiFiManager.get_current_status', async_get_status), \
         patch('src.api.routes.wifi.wifi_manager') as mock_wifi_manager:

        # Set up mock mode manager with scan results
        mock_mode_manager._scan_results = mock_networks
        mock_mode_manager.detect_current_mode = async_detect_mode
        mock_mode_manager.switch_mode = async_switch_mode
        mock_mode_manager.scan_from_ap_mode = async_scan

        # Set up mock wifi manager
        mock_wifi_manager.get_current_status = async_get_status
        mock_wifi_manager.connect_to_network = async_connect

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

        # 4. Get scan results
        response = client.get("/api/v1/wifi/scan-results")
        assert response.status_code == 200
        networks = response.json()["networks"]
        assert len(networks) == 2
        saved_network = next(n for n in networks if n["saved"])
        assert saved_network["ssid"] == "SavedNetwork"

        # 5. Connect to saved network
        response = client.post(
            "/api/v1/wifi/connect",
            json={"ssid": "SavedNetwork", "password": ""}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"

        # 6. Verify connection status
        response = client.get("/api/v1/wifi/current")
        assert response.status_code == 200
        connection = response.json()
        assert connection["ssid"] == "SavedNetwork"
        assert connection["is_connected"] is True

        # Verify the mocks were called correctly
        async_switch_mode.assert_called_once_with(NetworkMode.AP)
        async_scan.assert_called_once()
        async_connect.assert_called_once_with("SavedNetwork", "")