import pytest
from unittest.mock import MagicMock, call
from src.core.wifi_manager import WiFiManager
from src.core.models import WiFiStatus

@pytest.fixture
def wifi_manager():
    """Create a WiFiManager instance for testing"""
    return WiFiManager(skip_verify=True)

def test_get_current_status_connected(wifi_manager):
    """Test WiFi status when connected to a network"""
    # Mock the network manager responses
    wifi_manager._run_command = MagicMock()
    wifi_manager._run_command.return_value = MagicMock(
        returncode=0,
        stdout="MyNetwork:90:WPA2:*\nOtherNetwork:85:WPA2:no"
    )
    
    status = wifi_manager.get_current_status()
    assert status.ssid == "MyNetwork"
    assert status.is_connected is True
    assert len(status.available_networks) == 2

def test_get_current_status_disconnected(wifi_manager):
    """Test WiFi status when not connected"""
    wifi_manager._run_command = MagicMock()
    wifi_manager._run_command.return_value = MagicMock(
        returncode=0,
        stdout="Network1:80:WPA2:no\nNetwork2:75:WPA2:no"
    )
    
    status = wifi_manager.get_current_status()
    assert status.ssid is None
    assert status.is_connected is False
    assert len(status.available_networks) == 2

@pytest.mark.asyncio
async def test_connect_to_network(wifi_manager):
    """Test connecting to a WiFi network"""
    wifi_manager._run_command = MagicMock()
    # Note: Each call to get_current_status() needs both list and connectivity check responses
    wifi_manager._run_command.side_effect = [
        MagicMock(returncode=0, stdout=""),  # rescan
        MagicMock(returncode=0, stdout="TestNetwork:80:WPA2:no"),  # initial list
        MagicMock(returncode=0, stdout=""),  # connect
        MagicMock(returncode=0, stdout="TestNetwork:80:WPA2:*"),  # verify list
        MagicMock(returncode=0, stdout="full")  # connectivity check
    ]
    
    success = await wifi_manager.connect_to_network("TestNetwork", "password123")
    assert success is True
    
    # Verify all calls were made with correct arguments
    assert wifi_manager._run_command.call_args_list == [
        call(['sudo', 'nmcli', 'device', 'wifi', 'rescan'],
             capture_output=True, text=True, timeout=5),
        call(['sudo', 'nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY,IN-USE', 'device', 'wifi', 'list'],
             capture_output=True, text=True, timeout=5),
        call(['sudo', 'nmcli', 'device', 'wifi', 'connect', 'TestNetwork', 'password', 'password123'],
             capture_output=True, text=True, timeout=30),
        call(['sudo', 'nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY,IN-USE', 'device', 'wifi', 'list'],
             capture_output=True, text=True, timeout=5),
        call(['sudo', 'nmcli', 'networking', 'connectivity', 'check'],
             capture_output=True, text=True, timeout=5)
    ]

@pytest.mark.asyncio
async def test_connect_to_nonexistent_network(wifi_manager):
    """Test connecting to a non-existent network"""
    wifi_manager._run_command = MagicMock()
    wifi_manager._run_command.side_effect = [
        # First call: rescan
        MagicMock(returncode=0, stdout=""),
        # Second call: list networks
        MagicMock(returncode=0, stdout="Network1:75:WPA2:no\nNetwork2:70:WPA2:no")
    ]
    
    success = await wifi_manager.connect_to_network("NonExistentNetwork", "password123")
    assert success is False
    
    assert wifi_manager._run_command.call_args_list == [
        call(
            ['sudo', 'nmcli', 'device', 'wifi', 'rescan'],
            capture_output=True, text=True, timeout=5
        ),
        call(
            ['sudo', 'nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY,IN-USE', 'device', 'wifi', 'list'],
            capture_output=True, text=True, timeout=5
        )
    ]

def test_network_manager_not_running(wifi_manager):
    """Test behavior when network manager is not running"""
    wifi_manager._run_command = MagicMock(return_value=MagicMock(
        returncode=1,
        stderr="Network manager is not running"
    ))
    
    status = wifi_manager.get_current_status()
    assert status.ssid is None
    assert status.is_connected is False
    assert len(status.available_networks) == 0