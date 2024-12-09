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
        stdout="MyNetwork:90:WPA2:*\nMyNetwork:85:WPA2:no\nOtherNetwork:85:WPA2:no"
    )
    
    status = wifi_manager.get_current_status()
    assert status.ssid == "MyNetwork"
    assert status.is_connected is True
    # Expect only one entry per SSID
    assert len(status.available_networks) == 2
    assert any(net.ssid == "MyNetwork" and net.signal_strength == 90 for net in status.available_networks)

def test_get_current_status_disconnected(wifi_manager):
    """Test WiFi status when not connected"""
    wifi_manager._run_command = MagicMock()
    wifi_manager._run_command.return_value = MagicMock(
        returncode=0,
        stdout="Network1:80:WPA2:no\nNetwork1:75:WPA2:no\nNetwork2:75:WPA2:no"
    )
    
    status = wifi_manager.get_current_status()
    assert status.ssid is None
    assert status.is_connected is False
    # Expect only one entry per SSID
    assert len(status.available_networks) == 2
    assert any(net.ssid == "Network1" and net.signal_strength == 80 for net in status.available_networks)

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

def test_get_current_status_with_preconfigured_network(wifi_manager):
    """Test WiFi status with preconfigured network"""
    wifi_manager._run_command = MagicMock()
    wifi_manager._run_command.side_effect = [
        # First call - get saved connections with ALL info
        MagicMock(
            returncode=0,
            stdout=(
                "preconfigured:wifi:254c1f53-e84c-4273-b230-88b4935d5702:Salt_5GHz_D8261F\n"
                "Salt_2GHz_D8261F:wifi:f5471def-712c-4237-adbb-3a93df04cc93:Salt_2GHz_D8261F\n"
                "Wired connection 1:ethernet:0b9c02ee-fe6e-3a6d-9ba6-e614798bcaa6:"
            )
        ),
        # Second call - get current networks list
        MagicMock(
            returncode=0,
            stdout=(
                "Salt_2GHz_D8261F:82:WPA2:no\n"
                "Salt_5GHz_D8261F:82:WPA2:*"
            )
        ),
        # Third call - connectivity check
        MagicMock(returncode=0, stdout="full")
    ]
    
    wifi_manager.logger.setLevel(logging.DEBUG)
    status = wifi_manager.get_current_status()
    
    networks = {net.ssid: net for net in status.available_networks}
    assert networks["Salt_2GHz_D8261F"].saved is True
    assert networks["Salt_5GHz_D8261F"].saved is True
    assert networks["Salt_5GHz_D8261F"].in_use is True

def test_get_current_status_with_saved_networks(wifi_manager):
    """Test WiFi status with saved networks"""
    wifi_manager._run_command = MagicMock()
    wifi_manager._run_command.side_effect = [
        # First call - get saved networks
        MagicMock(
            returncode=0,
            stdout="preconfigured:wifi:254c1f53-e84c-4273-b230-88b4935d5702\n"
                   "Salt_2GHz_D8261F:wifi:f5471def-712c-4237-adbb-3a93df04cc93\n"
                   "Wired connection 1:ethernet:0b9c02ee-fe6e-3a6d-9ba6-e614798bcaa6"
        ),
        # Second call - get current networks
        MagicMock(
            returncode=0,
            stdout="Salt_2GHz_D8261F:84:WPA2:no\n"
                   "Salt_5GHz_D8261F:67:WPA2:*"
        ),
        # Third call - connectivity check
        MagicMock(returncode=0, stdout="full")
    ]
    
    wifi_manager.logger.setLevel(logging.DEBUG)
    status = wifi_manager.get_current_status()
    
    # Verify networks are correctly marked
    networks = {net.ssid: net for net in status.available_networks}
    assert networks["Salt_2GHz_D8261F"].saved is True
    assert networks["Salt_5GHz_D8261F"].saved is True  # Should be saved because it's in use
    assert networks["Salt_5GHz_D8261F"].in_use is True
    assert networks["Salt_2GHz_D8261F"].in_use is False

@pytest.mark.asyncio
async def test_failed_connection_gets_removed(wifi_manager):
    """Test that failed connection attempts are removed from saved networks"""
    wifi_manager._run_command = MagicMock()
    wifi_manager._run_command.side_effect = [
        MagicMock(returncode=0, stdout=""),  # rescan
        MagicMock(returncode=0, stdout=""),  # check saved networks
        MagicMock(returncode=0, stdout="TestNetwork:80:WPA2:no\n"),  # scan networks
        MagicMock(returncode=0, stdout=""),  # check saved networks again
        MagicMock(returncode=1, stdout="", stderr="Invalid password"),  # connect command fails
        MagicMock(returncode=0, stdout="GENERAL.STATE:20 (unavailable)"),  # verification check
        MagicMock(returncode=0, stdout="")  # remove connection
    ]
    
    success = await wifi_manager.connect_to_network("TestNetwork", "wrong_password")
    assert success is False
    
    # Verify that remove_connection was called with the correct arguments
    expected_call = call(['sudo', 'nmcli', 'connection', 'delete', 'TestNetwork'], 
                        capture_output=True, text=True)
    assert expected_call in wifi_manager._run_command.call_args_list

@pytest.mark.asyncio
async def test_verification_failure_removes_connection(wifi_manager):
    """Test that connections are removed if verification fails"""
    wifi_manager._run_command = MagicMock()
    wifi_manager._run_command.side_effect = [
        MagicMock(returncode=0, stdout=""),  # rescan
        MagicMock(returncode=0, stdout=""),  # check saved networks
        MagicMock(returncode=0, stdout="TestNetwork:80:WPA2:no\n"),  # scan networks
        MagicMock(returncode=0, stdout=""),  # check saved networks again
        MagicMock(returncode=0, stdout=""),  # connect command succeeds
        MagicMock(returncode=0, stdout="GENERAL.STATE:20 (unavailable)"),  # verification fails
        MagicMock(returncode=0, stdout="")  # remove connection
    ]
    
    success = await wifi_manager.connect_to_network("TestNetwork", "password123")
    assert success is False
    
    # Verify that remove_connection was called with the correct arguments
    expected_call = call(['sudo', 'nmcli', 'connection', 'delete', 'TestNetwork'], 
                        capture_output=True, text=True)
    assert expected_call in wifi_manager._run_command.call_args_list