import pytest
from unittest.mock import MagicMock, call
from src.core.models import WiFiStatus, NetworkMode, NetworkModeStatus
import logging

def test_get_current_status_connected(wifi_manager):
    """Test WiFi status when connected to a network"""
    wifi_manager._run_command = MagicMock()
    wifi_manager.get_operation_mode = MagicMock(return_value=NetworkModeStatus(
        mode=NetworkMode.DEFAULT,
        ap_ssid=None,
        ap_password=None,
        ip_address=None
    ))
    
    wifi_manager._run_command.side_effect = [
        # Get saved connections
        MagicMock(
            returncode=0,
            stdout="NAME:TYPE:FILENAME\nMyNetwork:wifi:/etc/NetworkManager/system-connections/MyNetwork.nmconnection"
        ),
        # Get available networks - Note the '*' indicating active connection
        MagicMock(
            returncode=0,
            stdout="MyNetwork:90:WPA2:*\nOtherNetwork:85:WPA2:no"
        ),
        # Internet connectivity check
        MagicMock(returncode=0, stdout="full")
    ]
    
    status = wifi_manager.get_current_status()
    assert status.ssid == "MyNetwork"
    assert status.is_connected is True
    assert len(status.available_networks) == 2
    assert any(net.ssid == "MyNetwork" and net.in_use for net in status.available_networks)

def test_get_current_status_in_ap_mode(wifi_manager):
    """Test WiFi status when in AP mode"""
    wifi_manager._run_command = MagicMock()
    # Mock get_operation_mode to return AP mode
    wifi_manager.get_operation_mode = MagicMock(return_value=NetworkModeStatus(
        mode=NetworkMode.AP,
        ap_ssid="RadioAP",
        ap_password="password123",
        ip_address="192.168.4.1"
    ))
    
    wifi_manager._run_command.side_effect = [
        # Get saved connections
        MagicMock(returncode=0, stdout="NAME:TYPE:FILENAME"),
        # Get available networks
        MagicMock(
            returncode=0,
            stdout="Network1:80:WPA2:no\nNetwork2:75:WPA2:no"
        )
    ]
    
    status = wifi_manager.get_current_status()
    assert status.ssid == "RadioAP"
    assert status.is_connected is True
    assert status.signal_strength == 100
    assert status.has_internet is False
    assert len(status.available_networks) == 2

def test_get_current_status_disconnected(wifi_manager):
    """Test WiFi status when not connected"""
    wifi_manager._run_command = MagicMock()
    wifi_manager.get_operation_mode = MagicMock(return_value=NetworkModeStatus(
        mode=NetworkMode.DEFAULT,
        ap_ssid=None,
        ap_password=None,
        ip_address=None
    ))
    
    wifi_manager._run_command.side_effect = [
        # Get saved connections
        MagicMock(returncode=0, stdout="NAME:TYPE:FILENAME"),
        # Get available networks - Note no '*' indicating no active connection
        MagicMock(
            returncode=0,
            stdout="Network1:80:WPA2:no\nNetwork2:75:WPA2:no"
        ),
        # Internet connectivity check not needed when disconnected
        MagicMock(returncode=1, stdout="")
    ]
    
    status = wifi_manager.get_current_status()
    assert status.ssid is None
    assert status.is_connected is False
    assert len(status.available_networks) == 2
    assert not any(net.in_use for net in status.available_networks)

@pytest.mark.asyncio
async def test_connect_to_network(wifi_manager):
    """Test connecting to a WiFi network"""
    wifi_manager._run_command = MagicMock()
    wifi_manager._run_command.side_effect = [
        # Check if in AP mode
        MagicMock(returncode=1, stdout="inactive"),  # Not in AP mode
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
        # Check if in AP mode
        MagicMock(returncode=1, stdout="inactive"),  # Not in AP mode
        # Connect command
        MagicMock(returncode=0, stdout=""),
        # Verify connection
        MagicMock(returncode=0, stdout="GENERAL.STATE:100 (connected)")
    ]
    
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
    # Mock get_operation_mode to return default mode
    wifi_manager.get_operation_mode = MagicMock(return_value=NetworkModeStatus(
        mode=NetworkMode.DEFAULT,
        ap_ssid=None,
        ap_password=None,
        ip_address=None
    ))
    
    wifi_manager._run_command.side_effect = [
        # Get saved connections
        MagicMock(
            returncode=0,
            stdout="NAME:TYPE:FILENAME\n"
                   "preconfigured:wifi:/etc/NetworkManager/system-connections/preconfigured.nmconnection"
        ),
        # Get preconfigured network config
        MagicMock(
            returncode=0,
            stdout="ssid=Salt_2GHz_D8261F"
        ),
        # Get available networks
        MagicMock(
            returncode=0,
            stdout="Salt_2GHz_D8261F:82:WPA2:no\nSalt_5GHz_D8261F:82:WPA2:*"
        ),
        # Internet connectivity check
        MagicMock(returncode=0, stdout="")
    ]
    
    status = wifi_manager.get_current_status()
    networks = {net.ssid: net for net in status.available_networks}
    assert networks["Salt_2GHz_D8261F"].saved is True

def test_get_current_status_with_saved_networks(wifi_manager):
    """Test WiFi status with saved networks"""
    wifi_manager._run_command = MagicMock()
    # Mock get_operation_mode to return default mode
    wifi_manager.get_operation_mode = MagicMock(return_value=NetworkModeStatus(
        mode=NetworkMode.DEFAULT,
        ap_ssid=None,
        ap_password=None,
        ip_address=None
    ))
    
    wifi_manager._run_command.side_effect = [
        # Get saved connections
        MagicMock(
            returncode=0,
            stdout="NAME:TYPE:FILENAME\n"
                   "Salt_2GHz_D8261F:wifi:/etc/NetworkManager/system-connections/salt2g.nmconnection"
        ),
        # Get available networks
        MagicMock(
            returncode=0,
            stdout="Salt_2GHz_D8261F:84:WPA2:no\nSalt_5GHz_D8261F:67:WPA2:*"
        ),
        # Internet connectivity check
        MagicMock(returncode=0, stdout="full")
    ]
    
    status = wifi_manager.get_current_status()
    networks = {net.ssid: net for net in status.available_networks}
    assert networks["Salt_2GHz_D8261F"].saved is True

@pytest.mark.asyncio
async def test_failed_connection_gets_removed(wifi_manager):
    """Test that failed connection attempts are removed from saved networks"""
    wifi_manager._run_command = MagicMock()
    wifi_manager._run_command.side_effect = [
        # Check if in AP mode
        MagicMock(returncode=0, stdout="inactive"),  # Not in AP mode
        # Get IP address
        MagicMock(returncode=0, stdout=""),
        # Rescan networks
        MagicMock(returncode=0, stdout=""),
        # Get network list
        MagicMock(returncode=0, stdout="TestNetwork:80:WPA2:no\n"),
        # Connect command fails
        MagicMock(returncode=1, stdout="", stderr="Invalid password"),
        # Remove connection
        MagicMock(returncode=0, stdout="")
    ]
    
    success = await wifi_manager.connect_to_network("TestNetwork", "wrong_password")
    assert success is False
    
    # Verify that remove_connection was called
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

@pytest.mark.asyncio
async def test_forget_network(wifi_manager):
    """Test forgetting a saved network"""
    wifi_manager._run_command = MagicMock()
    wifi_manager._run_command.side_effect = [
        # Delete connection command
        MagicMock(returncode=0, stdout="")
    ]
    
    result = wifi_manager._remove_connection("SavedNetwork")
    assert result is True
    
    # Verify correct command was called
    expected_call = call([
        'sudo', 'nmcli', 'connection', 'delete', 'SavedNetwork'
    ], capture_output=True, text=True)
    assert wifi_manager._run_command.call_args == expected_call

@pytest.mark.asyncio
async def test_forget_nonexistent_network(wifi_manager):
    """Test forgetting a non-existent network"""
    wifi_manager._run_command = MagicMock()
    wifi_manager._run_command.side_effect = [
        # Delete connection command fails
        MagicMock(returncode=1, stdout="", stderr="No such connection profile")
    ]
    
    result = wifi_manager._remove_connection("NonExistentNetwork")
    assert result is False

@pytest.mark.asyncio
async def test_connect_from_ap_mode_wrong_password(wifi_manager):
    """Test connecting with wrong password while in AP mode"""
    wifi_manager._run_command = MagicMock()
    wifi_manager._run_command.side_effect = [
        # Check AP mode status
        MagicMock(returncode=0, stdout="active"),
        # Get IP address
        MagicMock(returncode=0, stdout="inet 192.168.4.1/24"),
        # Disable AP mode
        MagicMock(returncode=0, stdout=""),
        # Rescan networks
        MagicMock(returncode=0, stdout=""),
        # Get network list
        MagicMock(returncode=0, stdout="TestNetwork:80:WPA2:no\n"),
        # Connect command fails
        MagicMock(returncode=1, stdout="", stderr="Invalid password"),
        # Remove connection
        MagicMock(returncode=0, stdout=""),
        # Enable AP mode again
        MagicMock(returncode=0, stdout="")
    ]
    
    success = await wifi_manager.connect_to_network("TestNetwork", "wrong_password")
    assert success is False
    
    # Verify AP mode was restored
    enable_ap_call = call(['sudo', 'systemctl', 'start', 'hostapd'], 
                         capture_output=True, text=True)
    assert enable_ap_call in wifi_manager._run_command.call_args_list

@pytest.mark.asyncio
async def test_connect_from_ap_mode_network_not_found(wifi_manager):
    """Test connecting to non-existent network while in AP mode"""
    wifi_manager._run_command = MagicMock()
    wifi_manager._run_command.side_effect = [
        # Check AP mode status
        MagicMock(returncode=0, stdout="active"),
        # Get IP address
        MagicMock(returncode=0, stdout="inet 192.168.4.1/24"),
        # Disable AP mode
        MagicMock(returncode=0, stdout=""),
        # Rescan networks
        MagicMock(returncode=0, stdout=""),
        # Get network list
        MagicMock(returncode=0, stdout="OtherNetwork:80:WPA2:no\n"),
        # Enable AP mode again
        MagicMock(returncode=0, stdout="")
    ]
    
    success = await wifi_manager.connect_to_network("NonExistentNetwork", "password123")
    assert success is False
    
    # Verify AP mode was restored
    enable_ap_call = call(['sudo', 'systemctl', 'start', 'hostapd'], 
                         capture_output=True, text=True)
    assert enable_ap_call in wifi_manager._run_command.call_args_list

@pytest.mark.asyncio
async def test_connect_from_ap_mode_disable_fails(wifi_manager):
    """Test connection when AP mode disable fails"""
    wifi_manager._run_command = MagicMock()
    wifi_manager._run_command.side_effect = [
        # Check AP mode status
        MagicMock(returncode=0, stdout="active"),
        # Get IP address
        MagicMock(returncode=0, stdout="inet 192.168.4.1/24"),
        # Disable AP mode fails
        MagicMock(returncode=1, stdout="", stderr="Failed to stop hostapd")
    ]
    
    success = await wifi_manager.connect_to_network("TestNetwork", "password123")
    assert success is False

@pytest.mark.asyncio
async def test_connect_from_ap_mode_success(wifi_manager):
    """Test successful connection from AP mode"""
    wifi_manager._run_command = MagicMock()
    wifi_manager._run_command.side_effect = [
        # Check AP mode status
        MagicMock(returncode=0, stdout="active"),
        # Disable AP mode
        MagicMock(returncode=0, stdout=""),
        # Connect command
        MagicMock(returncode=0, stdout=""),
        # Verify connection
        MagicMock(returncode=0, stdout="GENERAL.STATE:100 (connected)")
    ]
    
    success = await wifi_manager.connect_to_network("TestNetwork", "password123")
    assert success is True

@pytest.mark.asyncio
async def test_disable_ap_mode(wifi_manager):
    """Test disabling AP mode"""
    wifi_manager._run_command = MagicMock()
    wifi_manager._run_command.side_effect = [
        # Stop hostapd
        MagicMock(returncode=0, stdout=""),
        # Stop dnsmasq
        MagicMock(returncode=0, stdout=""),
        # Restart NetworkManager
        MagicMock(returncode=0, stdout=""),
        # Wait for NetworkManager to be ready
        MagicMock(returncode=0, stdout="NetworkManager is running")
    ]
    
    success = wifi_manager.disable_ap_mode()
    assert success is True
    
    # Verify correct sequence of commands
    expected_calls = [
        call(['sudo', 'systemctl', 'stop', 'hostapd'], capture_output=True, text=True),
        call(['sudo', 'systemctl', 'stop', 'dnsmasq'], capture_output=True, text=True),
        call(['sudo', 'systemctl', 'restart', 'NetworkManager'], capture_output=True, text=True),
    ]
    assert wifi_manager._run_command.call_args_list == expected_calls

@pytest.mark.asyncio
async def test_disable_ap_mode_failure(wifi_manager):
    """Test AP mode disable failure handling"""
    wifi_manager._run_command = MagicMock()
    wifi_manager._run_command.side_effect = [
        # hostapd stop fails
        MagicMock(returncode=1, stderr="Failed to stop hostapd"),
    ]
    
    success = wifi_manager.disable_ap_mode()
    assert success is False

@pytest.mark.asyncio
async def test_enable_ap_mode(wifi_manager):
    """Test enabling AP mode"""
    wifi_manager._run_command = MagicMock()
    wifi_manager._run_command.side_effect = [
        # Stop NetworkManager
        MagicMock(returncode=0, stdout=""),
        # Start hostapd
        MagicMock(returncode=0, stdout=""),
        # Start dnsmasq
        MagicMock(returncode=0, stdout=""),
        # Configure IP address
        MagicMock(returncode=0, stdout="")
    ]
    
    success = wifi_manager.enable_ap_mode(
        ssid="TestAP",
        password="testpass123",
        channel=1,
        ip="192.168.4.1"
    )
    assert success is True
    
    # Verify correct sequence of commands
    expected_calls = [
        call(['sudo', 'systemctl', 'stop', 'NetworkManager'], capture_output=True, text=True),
        call(['sudo', 'systemctl', 'start', 'hostapd'], capture_output=True, text=True),
        call(['sudo', 'systemctl', 'start', 'dnsmasq'], capture_output=True, text=True),
        call(['sudo', 'ip', 'addr', 'add', '192.168.4.1/24', 'dev', 'wlan0'], capture_output=True, text=True)
    ]
    assert wifi_manager._run_command.call_args_list == expected_calls

@pytest.mark.asyncio
async def test_enable_ap_mode_failure(wifi_manager):
    """Test AP mode enable failure handling"""
    wifi_manager._run_command = MagicMock()
    wifi_manager._run_command.side_effect = [
        # NetworkManager stop succeeds
        MagicMock(returncode=0, stdout=""),
        # hostapd start fails
        MagicMock(returncode=1, stderr="Failed to start hostapd"),
        # dnsmasq start (shouldn't be called but need to handle it)
        MagicMock(returncode=0, stdout=""),
        # IP address configuration (shouldn't be called but need to handle it)
        MagicMock(returncode=0, stdout=""),
        # NetworkManager restart on failure
        MagicMock(returncode=0, stdout="")
    ]
    
    success = wifi_manager.enable_ap_mode(
        ssid="TestAP",
        password="testpass123"
    )
    assert success is False
    
    # Verify NetworkManager is restarted on failure
    restart_call = call(['sudo', 'systemctl', 'restart', 'NetworkManager'], 
                       capture_output=True, text=True)
    assert restart_call in wifi_manager._run_command.call_args_list