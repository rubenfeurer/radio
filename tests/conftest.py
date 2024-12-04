import os
import pytest
from unittest.mock import MagicMock, PropertyMock

# Create module level mocks
mock_mpv_instance = None
mock_pi_instance = None

@pytest.fixture(autouse=True)
def mock_hardware(monkeypatch):
    """Mock hardware components for testing"""
    if os.getenv("GITHUB_ACTIONS") or os.getenv("MOCK_HARDWARE") == "true":
        global mock_mpv_instance, mock_pi_instance
        
        # Create fresh MPV mock
        mock_mpv_instance = MagicMock()
        mock_mpv_instance.play = MagicMock()
        mock_mpv_instance.stop = MagicMock()
        type(mock_mpv_instance).volume = PropertyMock(return_value=50)
        
        # Create MPV class mock
        mock_mpv = MagicMock()
        mock_mpv.MPV.return_value = mock_mpv_instance
        
        # Create fresh pigpio mock
        mock_pi_instance = MagicMock()
        mock_pi_instance.connected = True
        mock_pi_instance.read = MagicMock(return_value=1)
        mock_pi_instance.callback = MagicMock()
        mock_pi_instance.set_mode = MagicMock()
        mock_pi_instance.set_pull_up_down = MagicMock()
        
        # Add required constants
        mock_pi_instance.INPUT = 0
        mock_pi_instance.OUTPUT = 1
        mock_pi_instance.PUD_UP = 2
        mock_pi_instance.FALLING_EDGE = 3
        mock_pi_instance.RISING_EDGE = 4
        
        # Create pigpio module mock
        mock_pigpio = MagicMock()
        mock_pigpio.pi.return_value = mock_pi_instance
        
        # Patch both modules
        monkeypatch.setattr('mpv.MPV', mock_mpv.MPV)
        monkeypatch.setattr('pigpio.pi', mock_pigpio.pi)
        
        return {
            'mpv': mock_mpv_instance,
            'pi': mock_pi_instance
        }
    return None

# Add cleanup
@pytest.fixture(autouse=True)
def cleanup():
    yield
    global mock_mpv_instance, mock_pi_instance
    if mock_mpv_instance:
        mock_mpv_instance.reset_mock()
    if mock_pi_instance:
        mock_pi_instance.reset_mock()

@pytest.fixture
def mock_websocket():
    """Mock WebSocket for testing"""
    mock_ws = MagicMock()
    mock_ws.send = MagicMock()
    mock_ws.receive_json = MagicMock(return_value={"type": "status_request"})
    return mock_ws

@pytest.fixture
def mock_radio_manager():
    """Mock RadioManager for testing"""
    mock_manager = MagicMock()
    mock_manager.get_status.return_value = {
        "volume": 50,
        "current_station": None,
        "is_playing": False
    }
    return mock_manager