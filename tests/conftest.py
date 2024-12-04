import os
import pytest
from unittest.mock import MagicMock, PropertyMock

@pytest.fixture(autouse=True)
def mock_hardware():
    """Mock hardware components when MOCK_HARDWARE is set"""
    if os.getenv("MOCK_HARDWARE") == "true":
        # Mock MPV
        mock_mpv = MagicMock()
        # Set up volume property
        volume_property = PropertyMock(return_value=50)
        type(mock_mpv).volume = volume_property
        
        # Mock MPV class
        mock_mpv_class = MagicMock()
        mock_mpv_class.return_value = mock_mpv
        
        # Mock pigpio
        mock_pi = MagicMock()
        mock_pi.connected = True
        mock_pi.INPUT = 0
        mock_pi.OUTPUT = 1
        mock_pi.PUD_UP = 2
        mock_pi.FALLING_EDGE = 3
        mock_pi.RISING_EDGE = 4
        
        # Create a mock callback class
        class MockCallback:
            def __init__(self, *args, **kwargs):
                pass
            
            def cancel(self):
                pass
        
        mock_pi.callback = MockCallback
        
        # Patch the imports
        import sys
        sys.modules['pigpio'] = MagicMock()
        sys.modules['pigpio'].pi.return_value = mock_pi
        for attr in ['INPUT', 'OUTPUT', 'PUD_UP', 'FALLING_EDGE', 'RISING_EDGE']:
            setattr(sys.modules['pigpio'], attr, getattr(mock_pi, attr))
            
        sys.modules['mpv'] = MagicMock()
        sys.modules['mpv'].MPV = mock_mpv_class
        
        # Create a fixture dictionary to store mocks
        mocks = {
            'mpv': mock_mpv,
            'mpv_class': mock_mpv_class,
            'pi': mock_pi,
        }
        
        yield mocks
    else:
        yield None

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