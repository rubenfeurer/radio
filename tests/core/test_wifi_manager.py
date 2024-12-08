import pytest
from unittest.mock import MagicMock, call
from src.core.wifi_manager import WiFiManager
from src.core.models import WiFiStatus
import logging

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
    wifi_manager._run_command.side_effect = [
        MagicMock(returncode=0, stdout=""),  # rescan
        MagicMock(returncode=0, stdout=""),  # check saved networks
        MagicMock(returncode=0, stdout="TestNetwork:80:WPA2:no\n"),  # scan networks
        MagicMock(returncode=0, stdout=""),  # check saved networks again
        MagicMock(returncode=0, stdout=""),  # connect command
        MagicMock(returncode=0, stdout="GENERAL.STATE:100 (connected)")  # verify connection
    ]
    
    wifi_manager.logger.setLevel(logging.DEBUG)
    success = await wifi_manager.connect_to_network("TestNetwork", "password123")
    assert success is True

@pytest.mark.asyncio
async def test_connect_to_nonexistent_network(wifi_manager):
    """Test connecting to a non-existent network"""
    wifi_manager._run_command = MagicMock()
    wifi_manager._run_command.side_effect = [
        MagicMock(returncode=0, stdout=""),  # rescan
        MagicMock(returncode=0, stdout=""),  # check saved networks
        MagicMock(returncode=0, stdout="Network1:75:WPA2:no\nNetwork2:70:WPA2:no"),  # list networks
        MagicMock(returncode=0, stdout=""),  # connect attempt
        MagicMock(returncode=0, stdout="Network1:75:WPA2:no\nNetwork2:70:WPA2:no"),  # verify networks
        MagicMock(returncode=0, stdout="")  # saved networks for verification
    ]
    
    success = await wifi_manager.connect_to_network("NonExistentNetwork", "password123")
    assert success is False

@pytest.mark.asyncio
async def test_connect_to_saved_network(wifi_manager):
    """Test connecting to a saved network"""
    wifi_manager._run_command = MagicMock()
    wifi_manager._run_command.side_effect = [
        MagicMock(returncode=0, stdout=""),  # rescan
        MagicMock(returncode=0, stdout="SavedNetwork\n"),  # check saved networks
        MagicMock(returncode=0, stdout="SavedNetwork:80:WPA2:no\n"),  # scan networks
        MagicMock(returncode=0, stdout="SavedNetwork\n"),  # check saved networks again
        MagicMock(returncode=0, stdout=""),  # connect command
        MagicMock(returncode=0, stdout="GENERAL.STATE:100 (connected)")  # verify connection
    ]
    
    wifi_manager.logger.setLevel(logging.DEBUG)
    success = await wifi_manager.connect_to_network("SavedNetwork")
    assert success is True

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