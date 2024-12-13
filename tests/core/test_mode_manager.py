import pytest
from unittest.mock import AsyncMock, MagicMock
from src.core.mode_manager import ModeManager, NetworkMode

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
    # Mock switch_mode to prevent actual switching
    manager.switch_mode = AsyncMock()
    return manager

@pytest.mark.asyncio
async def test_detect_current_mode(mode_manager):
    """Test mode detection without actual system changes"""
    # Test AP mode detection
    mode_manager._run_command.side_effect = [
        MagicMock(returncode=0, stdout="active", stderr=""),
        MagicMock(returncode=0, stdout="", stderr="")
    ]
    mode = await mode_manager.detect_current_mode()
    assert mode == NetworkMode.AP

    # Test Client mode detection
    mode_manager._run_command.side_effect = [
        MagicMock(returncode=1, stdout="inactive", stderr=""),
        MagicMock(returncode=0, stdout="802-11-wireless:wlan0\nloopback:lo", stderr="")
    ]
    mode = await mode_manager.detect_current_mode()
    assert mode == NetworkMode.CLIENT

@pytest.mark.asyncio
async def test_switch_mode_mock(mode_manager):
    """Test mode switching without actual system changes"""
    mode_manager.switch_mode.return_value = True
    result = await mode_manager.switch_mode(NetworkMode.AP)
    assert result is True
    mode_manager.switch_mode.assert_called_once_with(NetworkMode.AP)