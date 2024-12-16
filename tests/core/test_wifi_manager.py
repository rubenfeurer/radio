import pytest
from unittest.mock import MagicMock, AsyncMock, call
from src.core.models import WiFiStatus, WiFiNetwork
import logging
import subprocess
from unittest.mock import patch
from src.core.wifi_manager import WiFiManager
from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport
from src.api.main import app

@pytest.mark.asyncio
async def test_get_current_status_connected(wifi_manager):
    """Test WiFi status when connected to a network"""
    wifi_manager._run_command = AsyncMock()
    wifi_manager._run_command.return_value = MagicMock(
        returncode=0,
        stdout="MyNetwork:90:WPA2:*\nMyNetwork:85:WPA2:no\nOtherNetwork:85:WPA2:no"
    )
    
    status = await wifi_manager.get_current_status()
    assert status.ssid == "MyNetwork"
    assert status.is_connected is True
    assert len(status.available_networks) == 2
    assert any(net.ssid == "MyNetwork" and net.signal_strength == 90 for net in status.available_networks)

@pytest.mark.asyncio
async def test_get_current_status_disconnected(wifi_manager):
    """Test WiFi status when not connected"""
    wifi_manager._run_command = AsyncMock()
    wifi_manager._run_command.return_value = MagicMock(
        returncode=0,
        stdout="Network1:80:WPA2:no\nNetwork1:75:WPA2:no\nNetwork2:75:WPA2:no"
    )
    
    status = await wifi_manager.get_current_status()
    assert status.ssid is None
    assert status.is_connected is False
    assert len(status.available_networks) == 2
    assert any(net.ssid == "Network1" and net.signal_strength == 80 for net in status.available_networks)

@pytest.mark.asyncio
async def test_connect_to_network():
    """Test successful network connection"""
    with patch('src.core.wifi_manager.WiFiManager.connect_to_network') as mock_connect, \
         patch('src.core.wifi_manager.WiFiManager.get_current_status') as mock_status:
        
        mock_connect.return_value = True
        mock_status.return_value = WiFiStatus(
            ssid="Salt_2GHz_D8261F",
            signal_strength=70,
            is_connected=True,
            has_internet=True,
            available_networks=[]
        )
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/wifi/connect",
                json={"ssid": "TestNetwork", "password": "TestPassword"})
        
        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "connected_ssid": "Salt_2GHz_D8261F"
        }
        mock_connect.assert_called_once_with("TestNetwork", "TestPassword")

@pytest.mark.asyncio
async def test_connect_to_nonexistent_network(wifi_manager):
    """Test connecting to a non-existent network"""
    wifi_manager._run_command = AsyncMock()
    wifi_manager._run_command.side_effect = [
        AsyncMock(returncode=0, stdout=""),  # rescan
        AsyncMock(returncode=0, stdout=""),  # check saved networks
        AsyncMock(returncode=0, stdout="Network1:75:WPA2:no\nNetwork2:70:WPA2:no"),  # list networks
        AsyncMock(returncode=0, stdout=""),  # connect attempt
        AsyncMock(returncode=0, stdout="Network1:75:WPA2:no\nNetwork2:70:WPA2:no"),  # verify networks
        AsyncMock(returncode=0, stdout="")  # saved networks for verification
    ]
    
    success = await wifi_manager.connect_to_network("NonExistentNetwork", "password123")
    assert success is False

@pytest.mark.asyncio
async def test_connect_to_saved_network(wifi_manager):
    """Test connecting to a saved network"""
    # Setup the mock
    mock_cmd = AsyncMock()
    mock_cmd.return_value = subprocess.CompletedProcess(
        args=[], returncode=0, stdout="GENERAL.STATE:100 (connected)", stderr=""
    )
    wifi_manager._run_command = mock_cmd
    
    wifi_manager.get_current_status = AsyncMock(return_value=WiFiStatus(
        available_networks=[
            WiFiNetwork(
                ssid="SavedNetwork",
                signal_strength=80,
                security="WPA2",
                in_use=False,
                saved=True
            )
        ]
    ))

    success = await wifi_manager.connect_to_network("SavedNetwork")
    assert success is True

@pytest.mark.asyncio
async def test_network_manager_not_running(wifi_manager):
    """Test behavior when network manager is not running"""
    wifi_manager._run_command = AsyncMock(return_value=MagicMock(
        returncode=1,
        stderr="Network manager is not running"
    ))
    
    status = await wifi_manager.get_current_status()
    assert status.ssid is None
    assert status.is_connected is False
    assert len(status.available_networks) == 0

@pytest.mark.asyncio
async def test_get_current_status_with_preconfigured_network(wifi_manager):
    """Test WiFi status with preconfigured network"""
    wifi_manager._run_command = AsyncMock()
    wifi_manager._run_command.side_effect = [
        # First call - list saved connections
        AsyncMock(
            returncode=0,
            stdout="NAME:TYPE:FILENAME\n"
                   "preconfigured:wifi:/etc/NetworkManager/system-connections/preconfigured.nmconnection\n"
                   "Salt_2GHz_D8261F:wifi:/etc/NetworkManager/system-connections/salt2g.nmconnection\n"
        ),
        # Second call - list available networks
        AsyncMock(
            returncode=0,
            stdout="Salt_2GHz_D8261F:82:WPA2:no\n"
                   "Salt_5GHz_D8261F:82:WPA2:*\n"
        ),
        # Third call - get network list for verification
        AsyncMock(
            returncode=0,
            stdout="Salt_2GHz_D8261F:82:WPA2:no\n"
                   "Salt_5GHz_D8261F:82:WPA2:*\n"
        ),
        # Internet check
        AsyncMock(returncode=0, stdout="")
    ]
    
    wifi_manager.logger.setLevel(logging.DEBUG)
    status = await wifi_manager.get_current_status()
    
    networks = {net.ssid: net for net in status.available_networks}
    assert networks["Salt_2GHz_D8261F"].saved is True
    assert networks["Salt_5GHz_D8261F"].saved is True
    assert networks["Salt_5GHz_D8261F"].in_use is True

@pytest.mark.asyncio
async def test_get_current_status_with_saved_networks(wifi_manager):
    """Test WiFi status with saved networks"""
    wifi_manager._run_command = AsyncMock()
    wifi_manager._run_command.side_effect = [
        # First call - list saved connections
        AsyncMock(
            returncode=0,
            stdout="NAME:TYPE:FILENAME\n"
                   "preconfigured:wifi:/etc/NetworkManager/system-connections/preconfigured.nmconnection\n"
                   "Salt_2GHz_D8261F:wifi:/etc/NetworkManager/system-connections/salt2g.nmconnection\n"
        ),
        # Second call - list available networks
        AsyncMock(
            returncode=0,
            stdout="Salt_2GHz_D8261F:84:WPA2:no\n"
                   "Salt_5GHz_D8261F:67:WPA2:*\n"
        ),
        # Third call - get network list for verification
        AsyncMock(
            returncode=0,
            stdout="Salt_2GHz_D8261F:84:WPA2:no\n"
                   "Salt_5GHz_D8261F:67:WPA2:*\n"
        ),
        # Internet check
        AsyncMock(returncode=0, stdout="")
    ]
    
    wifi_manager.logger.setLevel(logging.DEBUG)
    status = await wifi_manager.get_current_status()
    
    networks = {net.ssid: net for net in status.available_networks}
    assert networks["Salt_2GHz_D8261F"].saved is True
    assert networks["Salt_5GHz_D8261F"].saved is True
    assert networks["Salt_5GHz_D8261F"].in_use is True
    assert networks["Salt_2GHz_D8261F"].in_use is False

@pytest.mark.asyncio
async def test_failed_connection_gets_removed(wifi_manager):
    """Test that failed connections are removed"""
    wifi_manager._run_command = AsyncMock()
    wifi_manager.get_current_status = AsyncMock(return_value=WiFiStatus(
        available_networks=[
            WiFiNetwork(
                ssid="TestNetwork",
                signal_strength=80,
                security="WPA2",
                in_use=False,
                saved=False
            )
        ]
    ))
    
    wifi_manager._run_command.side_effect = [
        AsyncMock(returncode=0, stdout=""),  # rescan
        AsyncMock(returncode=1, stdout="", stderr="Invalid password"),  # connect command fails
        AsyncMock(returncode=0, stdout=""),  # delete connection
    ]

    success = await wifi_manager.connect_to_network("TestNetwork", "wrong_password")
    assert success is False

    # Verify remove_connection was called
    delete_calls = [call for call in wifi_manager._run_command.call_args_list
                   if 'connection' in str(call) and 'delete' in str(call)]
    assert len(delete_calls) > 0

@pytest.mark.asyncio
async def test_verification_failure_removes_connection(wifi_manager):
    """Test that connections are removed if verification fails"""
    wifi_manager._run_command = AsyncMock()
    wifi_manager.get_current_status = AsyncMock(return_value=WiFiStatus(
        available_networks=[
            WiFiNetwork(
                ssid="TestNetwork",
                signal_strength=80,
                security="WPA2",
                in_use=False,
                saved=False
            )
        ]
    ))
    
    wifi_manager._run_command.side_effect = [
        AsyncMock(returncode=0, stdout=""),  # rescan
        AsyncMock(returncode=0, stdout=""),  # connect command
        AsyncMock(returncode=0, stdout="GENERAL.STATE:20 (unavailable)"),  # verification fails
        AsyncMock(returncode=0, stdout=""),  # delete connection
    ]

    success = await wifi_manager.connect_to_network("TestNetwork", "password123")
    assert success is False

    # Verify remove_connection was called
    delete_calls = [call for call in wifi_manager._run_command.call_args_list
                   if 'connection' in str(call) and 'delete' in str(call)]
    assert len(delete_calls) > 0

@pytest.mark.asyncio
async def test_forget_network(wifi_manager):
    """Test forgetting a saved network"""
    mock_result = MagicMock(returncode=0, stdout="")
    
    async def mock_run(*args, **kwargs):
        return mock_result
    
    wifi_manager._run_command = mock_run
    result = await wifi_manager._remove_connection("SavedNetwork")
    assert result is True

@pytest.mark.asyncio
async def test_forget_nonexistent_network(wifi_manager):
    """Test forgetting a non-existent network"""
    mock_result = MagicMock(returncode=1, stdout="", stderr="No such connection profile")
    
    async def mock_run(*args, **kwargs):
        return mock_result
    
    wifi_manager._run_command = mock_run
    result = await wifi_manager._remove_connection("NonExistentNetwork")
    assert result is False

@pytest.mark.asyncio
async def test_get_preconfigured_ssid(wifi_manager):
    """Test getting preconfigured SSID"""
    wifi_manager._run_command = AsyncMock()
    wifi_manager._run_command.return_value = MagicMock(
        returncode=0,
        stdout="[connection]\nid=preconfigured\nssid=MyPreConfiguredNetwork\n"
    )
    
    ssid = await wifi_manager.get_preconfigured_ssid()
    assert ssid == "MyPreConfiguredNetwork"