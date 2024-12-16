import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.core.mode_manager import ModeManager, NetworkMode
import asyncio

@pytest.fixture
async def mode_manager():
    """Create a ModeManager with mocked command execution"""
    manager = ModeManager()
    # Mock the _run_command method to prevent actual system changes
    manager._run_command = AsyncMock()
    manager._run_command.return_value = MagicMock(
        returncode=0,
        stdout="",
        stderr=""
    )
    return manager

@pytest.mark.asyncio
async def test_switch_to_ap_mode(mode_manager):
    """Test switching to AP mode"""
    # Mock methods
    mode_manager._configure_interface = AsyncMock()
    mode_manager._configure_hostapd = AsyncMock()
    mode_manager._configure_dnsmasq = AsyncMock()
    mode_manager._verify_services = AsyncMock(return_value=True)
    
    # Execute switch
    result = await mode_manager.switch_to_ap_mode()
    
    # Verify results
    assert result is True
    assert mode_manager._current_mode == NetworkMode.AP
    
    # Verify service stop/start sequence
    calls = [' '.join(call.args[0]) for call in mode_manager._run_command.call_args_list]
    assert any('systemctl stop NetworkManager' in call for call in calls)
    assert any('systemctl stop wpa_supplicant' in call for call in calls)
    assert any('systemctl start hostapd' in call for call in calls)
    assert any('systemctl start dnsmasq' in call for call in calls)

@pytest.mark.asyncio
async def test_verify_services(mode_manager):
    """Test service verification"""
    # Mock AP mode service checks
    mode_manager._run_command.side_effect = [
        MagicMock(returncode=0, stdout="active"),  # hostapd
        MagicMock(returncode=0, stdout="active"),  # dnsmasq
        MagicMock(returncode=1, stdout="inactive") # wpa_supplicant
    ]
    
    result = await mode_manager._verify_services(NetworkMode.AP)
    assert result is True
    
    # Reset mock for CLIENT mode test
    mode_manager._run_command.reset_mock()
    mode_manager._run_command.side_effect = [
        MagicMock(returncode=0, stdout="active"),  # NetworkManager
        MagicMock(returncode=0, stdout="active")   # wpa_supplicant
    ]
    
    result = await mode_manager._verify_services(NetworkMode.CLIENT)
    assert result is True

@pytest.mark.asyncio
async def test_temp_switch_to_client_mode(mode_manager):
    """Test temporary switch to client mode"""
    mode_manager._current_mode = NetworkMode.AP
    mode_manager._switch_to_client = AsyncMock(return_value=True)
    
    result = await mode_manager.temp_switch_to_client_mode()
    
    assert result is True
    assert mode_manager._temp_mode_active is True
    assert mode_manager._previous_mode == NetworkMode.AP
    assert mode_manager.current_mode == NetworkMode.CLIENT

@pytest.mark.asyncio
async def test_restore_previous_mode(mode_manager):
    """Test restoring previous mode"""
    mode_manager._current_mode = NetworkMode.CLIENT
    mode_manager._previous_mode = NetworkMode.AP
    mode_manager._temp_mode_active = True
    mode_manager.switch_to_ap_mode = AsyncMock(return_value=True)
    
    result = await mode_manager.restore_previous_mode()
    
    assert result is True
    assert mode_manager._temp_mode_active is False
    assert mode_manager.current_mode == NetworkMode.AP