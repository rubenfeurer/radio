import pytest
from fastapi import HTTPException
from src.api.routes.ap_mode import get_network_mode, toggle_ap_mode
from src.core.models import NetworkMode, NetworkModeStatus

@pytest.mark.asyncio
async def test_get_network_mode_success(mock_wifi_manager_ap, mock_ap_mode_status):
    """Test successful network mode retrieval"""
    expected_status = mock_ap_mode_status()
    mock_wifi_manager_ap.get_operation_mode.return_value = expected_status
    
    result = await get_network_mode()
    
    assert result == expected_status
    mock_wifi_manager_ap.get_operation_mode.assert_called_once()

@pytest.mark.asyncio
async def test_get_network_mode_failure(mock_wifi_manager_ap):
    """Test network mode retrieval failure"""
    mock_wifi_manager_ap.get_operation_mode.side_effect = Exception("Network error")
    
    with pytest.raises(HTTPException) as exc_info:
        await get_network_mode()
    
    assert exc_info.value.status_code == 500
    assert "Failed to get network mode" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_toggle_ap_mode_to_ap(mock_wifi_manager_ap):
    """Test toggling from client to AP mode"""
    # Setup initial client mode and final AP mode states
    client_status = NetworkModeStatus(
        mode=NetworkMode.WIFI_CLIENT,
        is_connected=True,
        current_ssid="TestWiFi"
    )
    ap_status = NetworkModeStatus(
        mode=NetworkMode.AP,
        is_connected=True,
        ap_ip="192.168.4.1",
        is_ap_mode=True,
        ap_ssid="RadioAP"
    )
    
    mock_wifi_manager_ap.get_operation_mode.side_effect = [client_status, ap_status]
    mock_wifi_manager_ap.enable_ap_mode.return_value = True
    
    result = await toggle_ap_mode()
    
    assert result == ap_status
    mock_wifi_manager_ap.enable_ap_mode.assert_called_once()
    assert not mock_wifi_manager_ap.disable_ap_mode.called

@pytest.mark.asyncio
async def test_toggle_ap_mode_to_default(mock_wifi_manager_ap):
    """Test toggling from AP to client mode"""
    # Setup initial AP mode and final client mode states
    ap_status = NetworkModeStatus(
        mode=NetworkMode.AP,
        is_connected=True,
        ap_ip="192.168.4.1",
        is_ap_mode=True,
        ap_ssid="RadioAP"
    )
    client_status = NetworkModeStatus(
        mode=NetworkMode.WIFI_CLIENT,
        is_connected=True,
        current_ssid="TestWiFi"
    )
    
    mock_wifi_manager_ap.get_operation_mode.side_effect = [ap_status, client_status]
    mock_wifi_manager_ap.disable_ap_mode.return_value = True
    
    result = await toggle_ap_mode()
    
    assert result == client_status
    mock_wifi_manager_ap.disable_ap_mode.assert_called_once()
    assert not mock_wifi_manager_ap.enable_ap_mode.called 