import pytest
from unittest.mock import MagicMock, call, patch
from src.core.models import WiFiStatus, NetworkMode, NetworkModeStatus, WiFiNetwork
import logging
import subprocess
from asyncio import TimeoutError

@pytest.fixture
def wifi_manager():
    with patch('src.core.wifi_manager.WiFiManager._verify_networkmanager'), \
         patch('src.core.wifi_manager.WiFiManager._run_command'), \
         patch('src.core.wifi_manager.WiFiManager.get_preconfigured_ssid', return_value=None):
        from src.core.wifi_manager import WiFiManager
        return WiFiManager(skip_verify=True)

@patch('src.core.wifi_manager.WiFiManager.get_operation_mode')
@patch('src.core.wifi_manager.WiFiManager._run_command')
def test_get_current_status_connected(mock_run_command, mock_get_mode, wifi_manager):
    """Test getting WiFi status when connected"""
    # Setup operation mode
    mock_get_mode.return_value = NetworkModeStatus(
        mode=NetworkMode.WIFI_CLIENT, 
        is_connected=True,
        current_ssid="Network1"
    )
    
    mock_run_command.side_effect = [
        # Get saved connections
        MagicMock(returncode=0, stdout="Network1:802-11-wireless:file1\nNetwork2:802-11-wireless:file2"),
        # Get networks list
        MagicMock(returncode=0, stdout="Network1:80:WPA2:*\nNetwork2:75:WPA2:no"),
        # Check internet connectivity
        MagicMock(returncode=0, stdout="full")
    ]
    
    status = wifi_manager.get_current_status()
    assert status.ssid == "Network1"
    assert status.signal_strength == 80
    assert status.is_connected is True
    assert status.has_internet is True
    assert len(status.available_networks) == 2
    assert status.is_ap_mode is False

@patch('src.core.wifi_manager.WiFiManager.get_operation_mode')
@patch('src.core.wifi_manager.WiFiManager._run_command')
def test_get_current_status_in_ap_mode(mock_run_command, mock_get_mode, wifi_manager):
    """Test getting WiFi status in AP mode"""
    # Setup operation mode with all AP mode details
    mock_get_mode.return_value = NetworkModeStatus(
        mode=NetworkMode.AP, 
        is_connected=True,
        ap_ip="192.168.4.1",
        is_ap_mode=True,
        ap_ssid="RadioAP"
    )
    
    mock_run_command.side_effect = [
        # Get saved connections (not needed in AP mode)
        MagicMock(returncode=0, stdout=""),
        # Get networks list (empty in AP mode)
        MagicMock(returncode=0, stdout="")
    ]
    
    status = wifi_manager.get_current_status()
    assert status.is_ap_mode is True
    assert status.ap_ip == "192.168.4.1"
    assert status.ssid == "RadioAP"
    assert status.signal_strength == 100
    assert status.is_connected is True
    assert len(status.available_networks) == 0

@patch('src.core.wifi_manager.WiFiManager.get_operation_mode')
@patch('src.core.wifi_manager.WiFiManager._run_command')
def test_get_current_status_disconnected(mock_run_command, mock_get_mode, wifi_manager):
    """Test getting WiFi status when disconnected"""
    # Setup operation mode
    mock_get_mode.return_value = NetworkModeStatus(
        mode=NetworkMode.WIFI_CLIENT, 
        is_connected=False
    )
    
    mock_run_command.side_effect = [
        # Get saved connections
        MagicMock(returncode=0, stdout="Network1:802-11-wireless:file1"),
        # Get networks list
        MagicMock(returncode=0, stdout="Network1:80:WPA2:no\nNetwork2:75:WPA2:no")
    ]
    
    status = wifi_manager.get_current_status()
    assert status.ssid is None
    assert status.signal_strength is None
    assert status.is_connected is False
    assert status.has_internet is False
    assert len(status.available_networks) == 2
    assert status.is_ap_mode is False

@pytest.mark.asyncio
async def test_connect_to_network(wifi_manager):
    """Test connecting to a network"""
    wifi_manager._run_command = MagicMock()
    wifi_manager._run_command.side_effect = [
        # Check AP mode
        MagicMock(returncode=1, stdout="inactive"),
        # Connect command
        MagicMock(returncode=0, stdout=""),
        # Verify connection
        MagicMock(returncode=0, stdout="GENERAL.STATE:100 (connected)")
    ]
    
    success = await wifi_manager.connect_to_network("TestNetwork", "password123")
    assert success is True

@pytest.mark.asyncio
async def test_connect_to_nonexistent_network(wifi_manager):
    """Test connecting to a non-existent network"""
    wifi_manager._run_command = MagicMock()
    wifi_manager._run_command.side_effect = [
        # Check AP mode
        MagicMock(returncode=1, stdout="inactive"),
        # Connect attempt fails
        MagicMock(returncode=1, stderr="Error: Network not found")
    ]
    
    success = await wifi_manager.connect_to_network("NonExistentNetwork", "password123")
    assert success is False

@pytest.mark.asyncio
async def test_connect_to_saved_network(wifi_manager):
    """Test connecting to a saved network"""
    wifi_manager._run_command = MagicMock()
    wifi_manager._run_command.side_effect = [
        # Check AP mode
        MagicMock(returncode=1, stdout="inactive"),
        # Connect command
        MagicMock(returncode=0, stdout=""),
        # Verify connection
        MagicMock(returncode=0, stdout="GENERAL.STATE:100 (connected)")
    ]
    
    success = await wifi_manager.connect_to_network("SavedNetwork", None)
    assert success is True

def test_network_manager_not_running(wifi_manager):
    """Test initialization when NetworkManager is not running"""
    wifi_manager._run_command = MagicMock(return_value=MagicMock(returncode=1))
    
    with pytest.raises(RuntimeError, match="NetworkManager is not running"):
        wifi_manager._verify_networkmanager()

@pytest.mark.asyncio
async def test_remove_connection(wifi_manager):
    """Test removing a saved network"""
    wifi_manager._run_command = MagicMock(return_value=MagicMock(returncode=0, stdout=""))
    
    success = wifi_manager._remove_connection("SavedNetwork")
    assert success is True
    
    expected_call = call(['sudo', 'nmcli', 'connection', 'delete', 'SavedNetwork'], 
                        capture_output=True, text=True)
    assert expected_call in wifi_manager._run_command.call_args_list

@pytest.mark.asyncio
async def test_remove_nonexistent_connection(wifi_manager):
    """Test removing a non-existent network"""
    wifi_manager._run_command = MagicMock(return_value=MagicMock(
        returncode=1, 
        stderr="No such connection profile"
    ))
    
    success = wifi_manager._remove_connection("NonExistentNetwork")
    assert success is False

def test_aggregate_networks(wifi_manager):
    """Test network aggregation with duplicate SSIDs"""
    networks = [
        WiFiNetwork(ssid="Network1", signal_strength=80, security="WPA2", in_use=False),
        WiFiNetwork(ssid="Network1", signal_strength=70, security="WPA2", in_use=False),
        WiFiNetwork(ssid="Network2", signal_strength=90, security="WPA2", in_use=True),
    ]
    
    aggregated = wifi_manager._aggregate_networks(networks)
    assert len(aggregated) == 2
    assert any(n.ssid == "Network1" and n.signal_strength == 80 for n in aggregated)
    assert any(n.ssid == "Network2" and n.in_use for n in aggregated)

@pytest.mark.asyncio
async def test_rescan_networks(wifi_manager):
    """Test network rescan functionality"""
    wifi_manager._run_command = MagicMock()
    wifi_manager._run_command.side_effect = [
        MagicMock(returncode=0, stdout=""),  # Rescan command
        MagicMock(returncode=0, stdout="Network1:80:WPA2:no\nNetwork2:75:WPA2:no")  # Network list
    ]
    
    await wifi_manager._rescan_networks()
    
    # Verify rescan command was called
    expected_call = call([
        'sudo', 'nmcli', 'device', 'wifi', 'rescan'
    ], capture_output=True, text=True, timeout=5)
    assert wifi_manager._run_command.call_args_list[0] == expected_call

def test_parse_network_list(wifi_manager):
    """Test parsing of network list output"""
    saved_networks = {"SavedNetwork", "AnotherSaved"}
    output = "SavedNetwork:85:WPA2:*\nNewNetwork:75:WPA2:no\nAnotherSaved:70:WPA2:no"
    
    networks = wifi_manager._parse_network_list(output, saved_networks)
    
    assert len(networks) == 3
    saved_net = next(n for n in networks if n.ssid == "SavedNetwork")
    new_net = next(n for n in networks if n.ssid == "NewNetwork")
    another_saved = next(n for n in networks if n.ssid == "AnotherSaved")
    
    assert saved_net.saved is True
    assert saved_net.in_use is True
    assert new_net.saved is False
    assert another_saved.saved is True

def test_run_command_timeout(wifi_manager):
    """Test command execution with timeout"""
    try:
        wifi_manager._run_command(['sleep', '10'], timeout=1)
        pytest.fail("Expected TimeoutExpired exception")
    except subprocess.TimeoutExpired:
        pass

def test_run_command_error(wifi_manager):
    """Test command execution with error"""
    try:
        result = wifi_manager._run_command(['nonexistent_command'])
        assert result.returncode != 0
    except FileNotFoundError:
        # This is also an acceptable outcome
        pass
    except Exception as e:
        pytest.fail(f"Unexpected exception: {e}")

@pytest.mark.asyncio
async def test_connect_command_timeout(wifi_manager):
    """Test network connection with timeout"""
    wifi_manager._run_command = MagicMock(side_effect=TimeoutError())
    
    success = await wifi_manager.connect_to_network("TestNetwork", "password123")
    assert success is False

def test_get_preconfigured_ssid(wifi_manager):
    """Test getting preconfigured network SSID"""
    wifi_manager._run_command = MagicMock()
    wifi_manager._run_command.return_value = MagicMock(
        returncode=0,
        stdout="[connection]\nid=preconfigured\ntype=wifi\n\n[wifi]\nssid=PreConfiguredNet\nmode=infrastructure\n"
    )
    
    ssid = wifi_manager.get_preconfigured_ssid()
    assert ssid == "PreConfiguredNet"
    
    # Test with missing config file
    wifi_manager._run_command.return_value = MagicMock(returncode=1, stderr="No such file")
    assert wifi_manager.get_preconfigured_ssid() is None