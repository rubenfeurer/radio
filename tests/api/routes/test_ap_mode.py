import pytest
from fastapi import HTTPException
from unittest.mock import patch, MagicMock
from src.api.routes.ap_mode import (
    get_network_mode, 
    toggle_ap_mode, 
    scan_networks_in_ap_mode,
    get_ap_status
)
from src.core.models import NetworkMode, NetworkModeStatus, WiFiNetwork, WiFiStatus

@pytest.mark.asyncio
async def test_get_network_mode_success(mock_wifi_manager_ap):
    """Test successful network mode retrieval"""
    expected_status = NetworkModeStatus(mode=NetworkMode.AP, ip_address="192.168.4.1")
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
async def test_scan_networks_in_ap_mode_success():
    """Test successful network scanning in AP mode"""
    mock_scan_output = """
BSS 00:11:22:33:44:55(on wlan0)
    SSID: TestNetwork1
    signal: -50.00 dBm
BSS 66:77:88:99:aa:bb(on wlan0)
    SSID: TestNetwork2
    signal: -70.00 dBm
"""
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = mock_scan_output
    
    with patch('subprocess.run', return_value=mock_process):
        result = await scan_networks_in_ap_mode()
        
        assert len(result) == 2
        assert result[0].ssid == "TestNetwork1"
        assert result[0].signal_strength == 100  # -50 dBm converted to percentage
        assert result[1].ssid == "TestNetwork2"
        assert result[1].signal_strength == 60   # -70 dBm converted to percentage

@pytest.mark.asyncio
async def test_scan_networks_in_ap_mode_failure():
    """Test network scanning failure in AP mode"""
    mock_process = MagicMock()
    mock_process.returncode = 1
    mock_process.stderr = "Failed to scan"
    
    with patch('subprocess.run', return_value=mock_process):
        with pytest.raises(HTTPException) as exc_info:
            await scan_networks_in_ap_mode()
        
        assert exc_info.value.status_code == 500
        assert "Network scan failed" in str(exc_info.value.detail)

@pytest.mark.asyncio
async def test_get_ap_status_active():
    """Test AP status when hostapd is active"""
    mock_hostapd_check = MagicMock()
    mock_hostapd_check.returncode = 0
    
    # Mock iwlist scan output
    mock_scan_output = """
Cell 01 - Address: 00:11:22:33:44:55
    ESSID:"TestNetwork1"
    Quality=70/70  Signal level=-30 dBm  
    Encryption key:on
Cell 02 - Address: 66:77:88:99:AA:BB
    ESSID:"TestNetwork2"
    Quality=50/70  Signal level=-60 dBm  
    Encryption key:off
"""
    mock_scan = MagicMock()
    mock_scan.returncode = 0
    mock_scan.stdout = mock_scan_output
    
    with patch('subprocess.run') as mock_run:
        def mock_run_command(*args, **kwargs):
            if 'hostapd' in args[0]:
                return mock_hostapd_check
            elif 'iwlist' in args[0]:
                return mock_scan
            return MagicMock(returncode=0)
            
        mock_run.side_effect = mock_run_command
        
        with patch('src.api.routes.ap_mode.settings.AP_SSID', "TestAP"):
            result = await get_ap_status()
            
            assert isinstance(result, WiFiStatus)
            assert result.ssid == "TestAP"
            assert result.signal_strength == 100
            assert result.is_connected is True
            assert result.has_internet is False
            assert len(result.available_networks) == 2
            
            # Verify network details
            networks = result.available_networks
            assert networks[0].ssid == "TestNetwork1"
            assert networks[0].signal_strength == 100  # 70/70 = 100%
            assert networks[0].security == "WPA2"
            
            assert networks[1].ssid == "TestNetwork2"
            assert networks[1].signal_strength == 71   # 50/70 ≈ 71%
            assert networks[1].security is None

@pytest.mark.asyncio
async def test_get_ap_status_inactive():
    """Test AP status when hostapd is inactive"""
    mock_hostapd_check = MagicMock()
    mock_hostapd_check.returncode = 1
    
    with patch('subprocess.run', return_value=mock_hostapd_check):
        result = await get_ap_status()
        
        assert isinstance(result, WiFiStatus)
        assert result.ssid is None
        assert result.is_connected is False
        assert len(result.available_networks) == 0

@pytest.mark.asyncio
async def test_get_ap_status_scan_failure():
    """Test AP status when network scan fails"""
    mock_hostapd_check = MagicMock()
    mock_hostapd_check.returncode = 0
    
    mock_scan = MagicMock()
    mock_scan.returncode = 1
    mock_scan.stderr = "Failed to scan"
    
    with patch('subprocess.run') as mock_run:
        def mock_run_command(*args, **kwargs):
            if 'hostapd' in args[0]:
                return mock_hostapd_check
            elif 'iwlist' in args[0]:
                return mock_scan
            return MagicMock(returncode=0)
            
        mock_run.side_effect = mock_run_command
        
        with patch('src.api.routes.ap_mode.settings.AP_SSID', "TestAP"):
            result = await get_ap_status()
            
            assert isinstance(result, WiFiStatus)
            assert result.ssid == "TestAP"
            assert result.is_connected is True
            assert len(result.available_networks) == 0

@pytest.mark.asyncio
async def test_toggle_ap_mode_to_ap(mock_wifi_manager_ap):
    """Test toggling from default to AP mode"""
    mock_settings = MagicMock()
    mock_settings.AP_SSID = "TestAP"
    mock_settings.AP_PASSWORD = "testpass"
    mock_settings.AP_IP = "192.168.4.1"
    
    with patch('src.api.routes.ap_mode.wifi_manager', mock_wifi_manager_ap), \
         patch('src.api.routes.ap_mode.settings', mock_settings):
        
        default_status = NetworkModeStatus(mode=NetworkMode.DEFAULT, ip_address="192.168.1.100")
        
        mock_wifi_manager_ap.get_operation_mode.side_effect = [default_status]
        mock_wifi_manager_ap.enable_ap_mode.return_value = True
        
        result = await toggle_ap_mode()
        
        assert result.mode == NetworkMode.AP
        assert result.ap_ssid == "TestAP"
        assert result.ap_password == "testpass"
        mock_wifi_manager_ap.enable_ap_mode.assert_called_once_with(
            ssid="TestAP",
            password="testpass",
            ip="192.168.4.1"
        )
        assert not mock_wifi_manager_ap.disable_ap_mode.called

@pytest.mark.asyncio
async def test_toggle_ap_mode_to_default(mock_wifi_manager_ap):
    """Test toggling from AP to default mode"""
    with patch('src.api.routes.ap_mode.wifi_manager', mock_wifi_manager_ap):
        ap_status = NetworkModeStatus(
            mode=NetworkMode.AP,
            ap_ssid="TestAP",
            ap_password="testpass",
            ip_address="192.168.4.1"
        )
        
        mock_wifi_manager_ap.get_operation_mode.side_effect = [ap_status]
        mock_wifi_manager_ap.disable_ap_mode.return_value = True
        mock_wifi_manager_ap.get_ip_address.return_value = "192.168.1.100"
        
        result = await toggle_ap_mode()
        
        assert result.mode == NetworkMode.DEFAULT
        mock_wifi_manager_ap.disable_ap_mode.assert_called_once()
        assert not mock_wifi_manager_ap.enable_ap_mode.called