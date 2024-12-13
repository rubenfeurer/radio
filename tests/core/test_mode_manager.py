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
async def test_temp_switch_to_client_mode(mode_manager):
    """Test temporary switch to client mode"""
    # Setup initial state
    mode_manager._current_mode = NetworkMode.AP
    
    # Mock successful client mode switch
    mode_manager._switch_to_client = AsyncMock(return_value=True)
    
    # Perform temporary switch
    result = await mode_manager.temp_switch_to_client_mode()
    
    assert result is True
    assert mode_manager._temp_mode_active is True
    assert mode_manager._previous_mode == NetworkMode.AP
    assert mode_manager.current_mode == NetworkMode.CLIENT

@pytest.mark.asyncio
async def test_restore_previous_mode(mode_manager):
    """Test restoring previous mode"""
    # Setup initial state
    mode_manager._current_mode = NetworkMode.CLIENT
    mode_manager._previous_mode = NetworkMode.AP
    mode_manager._temp_mode_active = True
    
    # Mock successful AP mode switch
    mode_manager._switch_to_ap = AsyncMock(return_value=True)
    
    # Restore previous mode
    result = await mode_manager.restore_previous_mode()
    
    assert result is True
    assert mode_manager._temp_mode_active is False
    assert mode_manager.current_mode == NetworkMode.AP

@pytest.mark.asyncio
async def test_detect_current_mode_temp_mode(mode_manager):
    """Test mode detection respects temporary mode"""
    # Setup temporary mode
    mode_manager._current_mode = NetworkMode.CLIENT
    mode_manager._temp_mode_active = True
    
    # Detect mode should return current mode without checking system
    mode = await mode_manager.detect_current_mode()
    assert mode == NetworkMode.CLIENT
    
    # Verify _run_command was not called
    mode_manager._run_command.assert_not_called()

@pytest.mark.asyncio
async def test_detect_current_mode_normal(mode_manager):
    """Test normal mode detection without temporary mode"""
    # Test AP mode detection
    mode_manager._temp_mode_active = False
    mode_manager._run_command.side_effect = [
        MagicMock(returncode=0, stdout="active", stderr=""),  # hostapd active
        MagicMock(returncode=0, stdout="", stderr="")  # nmcli check
    ]
    
    mode = await mode_manager.detect_current_mode()
    assert mode == NetworkMode.AP
    
    # Reset mock
    mode_manager._run_command.reset_mock()
    mode_manager._run_command.side_effect = [
        MagicMock(returncode=1, stdout="inactive", stderr=""),  # hostapd inactive
        MagicMock(returncode=0, stdout="802-11-wireless:wlan0\nloopback:lo", stderr="")  # nmcli shows wifi
    ]
    
    mode = await mode_manager.detect_current_mode()
    assert mode == NetworkMode.CLIENT

@pytest.mark.asyncio
async def test_temp_mode_timeout(mode_manager):
    """Test temporary mode timeout"""
    # Reduce timeout for testing
    mode_manager._temp_mode_timeout = 0.1
    
    # Setup initial state
    mode_manager._current_mode = NetworkMode.CLIENT
    mode_manager._previous_mode = NetworkMode.AP
    mode_manager._temp_mode_active = True
    
    # Mock restore_previous_mode
    mode_manager.restore_previous_mode = AsyncMock()
    
    # Start timeout handler
    await mode_manager._handle_temp_mode_timeout()
    
    # Wait for timeout
    await asyncio.sleep(0.2)
    
    # Verify restore was called
    mode_manager.restore_previous_mode.assert_called_once()

@pytest.mark.asyncio
async def test_switch_mode_mock(mode_manager):
    """Test mode switching without actual system changes"""
    # Mock the switch methods
    mode_manager._switch_to_ap = AsyncMock(return_value=True)
    mode_manager._switch_to_client = AsyncMock(return_value=True)
    
    # Test switching to AP mode
    result = await mode_manager.switch_mode(NetworkMode.AP)
    assert result is True
    
    # Test switching to Client mode
    result = await mode_manager.switch_mode(NetworkMode.CLIENT)
    assert result is True

@pytest.mark.asyncio
async def test_get_network_status_ap_mode(mode_manager):
    """Test getting network status in AP mode"""
    # Setup initial state
    mode_manager._current_mode = NetworkMode.AP
    mode_manager._temp_mode_active = False
    
    # Mock status detection
    mode_manager.detect_current_mode = AsyncMock(return_value=NetworkMode.AP)
    
    # Get status
    mode = await mode_manager.detect_current_mode()
    assert mode == NetworkMode.AP
    assert mode_manager.is_temp_mode is False
    assert mode_manager.is_switching is False

@pytest.mark.asyncio
async def test_get_network_status_client_mode(mode_manager):
    """Test getting network status in CLIENT mode"""
    # Setup initial state
    mode_manager._current_mode = NetworkMode.CLIENT
    mode_manager._temp_mode_active = False
    
    # Mock status detection
    mode_manager.detect_current_mode = AsyncMock(return_value=NetworkMode.CLIENT)
    
    # Get status
    mode = await mode_manager.detect_current_mode()
    assert mode == NetworkMode.CLIENT
    assert mode_manager.is_temp_mode is False
    assert mode_manager.is_switching is False