import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from src.core.mode_manager import ModeManager, NetworkMode
import tempfile
import os

@pytest.fixture
async def mode_manager():
    manager = ModeManager()
    manager._run_command = AsyncMock()
    return manager

@pytest.mark.asyncio
async def test_switch_to_ap_mode(mode_manager):
    """Test switching to AP mode"""
    # Mock successful command executions
    mode_manager._run_command.return_value = MagicMock(
        returncode=0,
        stdout="",
        stderr=""
    )
    
    success = await mode_manager.switch_mode(NetworkMode.AP)
    assert success is True
    
    # Verify all necessary commands were called
    expected_calls = [
        call(['sudo', 'systemctl', 'stop', 'NetworkManager']),
        call(['sudo', 'systemctl', 'start', 'hostapd']),
        call(['sudo', 'systemctl', 'start', 'dnsmasq']),
        call(['sudo', 'sysctl', 'net.ipv4.ip_forward=1']),
        call(['sudo', 'ip', 'addr', 'flush', 'dev', 'wlan0']),
        call(['sudo', 'ip', 'addr', 'add', '192.168.4.1/24', 'dev', 'wlan0']),
        call(['sudo', 'ip', 'link', 'set', 'wlan0', 'up'])
    ]
    
    for expected_call in expected_calls:
        assert expected_call in mode_manager._run_command.call_args_list

@pytest.mark.asyncio
async def test_switch_to_client_mode(mode_manager):
    """Test switching to client mode"""
    mode_manager._run_command.return_value = MagicMock(
        returncode=0,
        stdout="",
        stderr=""
    )
    
    success = await mode_manager.switch_mode(NetworkMode.CLIENT)
    assert success is True
    
    expected_calls = [
        call(['sudo', 'systemctl', 'stop', 'hostapd']),
        call(['sudo', 'systemctl', 'stop', 'dnsmasq']),
        call(['sudo', 'sysctl', 'net.ipv4.ip_forward=0']),
        call(['sudo', 'ip', 'addr', 'flush', 'dev', 'wlan0']),
        call(['sudo', 'ip', 'link', 'set', 'wlan0', 'up']),
        call(['sudo', 'systemctl', 'start', 'NetworkManager'])
    ]
    
    for expected_call in expected_calls:
        assert expected_call in mode_manager._run_command.call_args_list

@pytest.mark.asyncio
async def test_detect_current_mode(mode_manager):
    """Test mode detection"""
    # Test AP mode detection
    mode_manager._run_command.return_value = MagicMock(
        stdout="AP mode active",
        stderr="",
        returncode=0
    )
    mode = await mode_manager.detect_current_mode()
    assert mode == NetworkMode.AP
    
    # Test Client mode detection
    mode_manager._run_command.return_value = MagicMock(
        stdout="managed mode",
        stderr="",
        returncode=0
    )
    mode = await mode_manager.detect_current_mode()
    assert mode == NetworkMode.CLIENT

@pytest.mark.asyncio
async def test_configure_hostapd(mode_manager):
    """Test hostapd configuration"""
    with patch('tempfile.NamedTemporaryFile', create=True) as mock_temp:
        mock_temp.return_value.__enter__.return_value.name = '/tmp/test_hostapd.conf'
        await mode_manager._configure_hostapd()
        
        expected_calls = [
            call(['sudo', 'mv', '/tmp/test_hostapd.conf', '/etc/hostapd/hostapd.conf']),
            call(['sudo', 'chmod', '600', '/etc/hostapd/hostapd.conf'])
        ]
        
        for expected_call in expected_calls:
            assert expected_call in mode_manager._run_command.call_args_list

@pytest.mark.asyncio
async def test_configure_dnsmasq(mode_manager):
    """Test dnsmasq configuration"""
    with patch('tempfile.NamedTemporaryFile', create=True) as mock_temp:
        mock_temp.return_value.__enter__.return_value.name = '/tmp/test_dnsmasq.conf'
        await mode_manager._configure_dnsmasq()
        
        expected_call = call(['sudo', 'mv', '/tmp/test_dnsmasq.conf', '/etc/dnsmasq.conf'])
        assert expected_call in mode_manager._run_command.call_args_list

@pytest.mark.asyncio
async def test_cleanup_on_failure(mode_manager):
    """Test cleanup when AP mode switch fails"""
    # Setup mock to fail on first call but succeed on cleanup calls
    call_count = 0
    async def mock_command(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:  # Fail on the second call (after mode detection)
            raise Exception("Command failed")
        return MagicMock(returncode=0, stdout="", stderr="")

    mode_manager._run_command = AsyncMock(side_effect=mock_command)
    
    success = await mode_manager.switch_mode(NetworkMode.AP)
    assert success is False
    
    # Verify cleanup was attempted
    cleanup_calls = [
        call(['sudo', 'systemctl', 'stop', 'hostapd']),
        call(['sudo', 'systemctl', 'stop', 'dnsmasq']),
        call(['sudo', 'systemctl', 'start', 'NetworkManager']),
        call(['sudo', 'ip', 'addr', 'flush', 'dev', 'wlan0']),
        call(['sudo', 'ip', 'link', 'set', 'wlan0', 'up'])
    ]
    
    # Get all calls after the failure
    actual_calls = mode_manager._run_command.call_args_list[2:]
    
    # Verify that all cleanup calls were made (in any order)
    for cleanup_call in cleanup_calls:
        assert cleanup_call in actual_calls, f"Missing cleanup call: {cleanup_call}"

@pytest.mark.asyncio
async def test_concurrent_switch_prevention(mode_manager):
    """Test prevention of concurrent mode switches"""
    # Start a switch operation
    mode_manager._switching = True
    
    # Attempt another switch
    success = await mode_manager.switch_mode(NetworkMode.AP)
    assert success is False
    assert mode_manager._run_command.call_count == 0