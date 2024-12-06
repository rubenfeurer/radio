import pytest
from unittest.mock import patch, MagicMock, call
import unittest
from src.core.wifi_manager import WiFiManager
from src.core.models import WiFiStatus, WiFiNetwork

def test_get_current_status_connected(wifi_manager):
    """Test WiFi status when connected to a network"""
    status = wifi_manager.get_current_status()
    
    assert status.ssid == "MyNetwork"
    assert status.signal_strength == 90
    assert status.is_connected is True
    assert status.has_internet is True
    assert len(status.available_networks) == 3

def test_get_current_status_disconnected(wifi_manager, mock_networkmanager):
    """Test WiFi status when not connected"""
    # Override the mock for disconnected state
    mock_networkmanager.side_effect = lambda *args, **kwargs: MagicMock(
        returncode=0,
        stderr="",
        stdout=(
            "" if "rescan" in args[0] else
            "Network1:80:WPA2::no\nNetwork2:75:WPA2::no" if "list" in args[0] and "ifname" not in args[0] else
            ""  # No current connection
        )
    )
    
    status = wifi_manager.get_current_status()
    
    assert status.ssid is None
    assert status.is_connected is False
    assert len(status.available_networks) == 2

def test_network_manager_not_running():
    """Test initialization when NetworkManager is not running"""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="inactive",
            stderr="NetworkManager is not running"
        )
        
        with pytest.raises(RuntimeError, match="NetworkManager is not running"):
            WiFiManager()

@pytest.mark.asyncio
async def test_connect_to_network(wifi_manager, mock_networkmanager):
    """Test connecting to a WiFi network"""
    # Reset mock to clear initialization calls
    mock_networkmanager.reset_mock()
    
    # Mock successful connection with correct format matching _scan_networks method
    mock_networkmanager.side_effect = [
        # First call: network scan rescan
        MagicMock(returncode=0, stdout=""),
        # Second call: network list
        MagicMock(
            returncode=0,
            stdout="TestNetwork:80:WPA2:*\nNetwork2:75:WPA2:no"
        ),
        # Third call: connection attempt
        MagicMock(returncode=0, stdout="Success"),
        # Fourth call: verification list
        MagicMock(
            returncode=0,
            stdout="TestNetwork:80:WPA2:*"
        )
    ]
    
    success = await wifi_manager.connect_to_network("TestNetwork", "password123")
    assert success is True

    # Verify the correct sequence of commands
    assert mock_networkmanager.call_args_list == [
        # First: Rescan
        call(
            ['nmcli', 'device', 'wifi', 'rescan'],
            capture_output=True, text=True, timeout=5
        ),
        # Second: List networks
        call(
            ['nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY,IN-USE', 'device', 'wifi', 'list'],
            capture_output=True, text=True, timeout=5
        ),
        # Third: Connect
        call(
            ['nmcli', 'device', 'wifi', 'connect', 'TestNetwork', 
             'password', 'password123', 'ifname', 'wlan0'],
            capture_output=True, text=True, timeout=5
        ),
        # Fourth: Verify connection
        call(
            ['nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY', 'device', 'wifi', 
             'list', 'ifname', 'wlan0'],
            capture_output=True, text=True, timeout=5
        )
    ]

@pytest.mark.asyncio
async def test_connect_to_nonexistent_network(wifi_manager, mock_networkmanager):
    """Test connecting to a non-existent network"""
    # Reset mock to clear initialization calls
    mock_networkmanager.reset_mock()
    
    # Mock scan results without the target network
    mock_networkmanager.side_effect = [
        # First call: rescan
        MagicMock(returncode=0, stdout=""),
        # Second call: list networks
        MagicMock(
            returncode=0,
            stdout="Network1:75:WPA2:no\nNetwork2:70:WPA2:no"
        )
    ]
    
    success = await wifi_manager.connect_to_network("NonExistentNetwork", "password123")
    assert success is False

    # Verify only scan commands were called
    assert mock_networkmanager.call_args_list == [
        # First: Rescan
        call(
            ['nmcli', 'device', 'wifi', 'rescan'],
            capture_output=True, text=True, timeout=5
        ),
        # Second: List networks
        call(
            ['nmcli', '-t', '-f', 'SSID,SIGNAL,SECURITY,IN-USE', 'device', 'wifi', 'list'],
            capture_output=True, text=True, timeout=5
        )
    ]