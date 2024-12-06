import pytest
from unittest.mock import patch, MagicMock
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