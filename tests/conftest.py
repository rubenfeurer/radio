import os
import sys
import pytest
from unittest.mock import Mock

# Add the project root directory to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

@pytest.fixture
def mock_gpio():
    """Provide a mock GPIO interface for testing"""
    mock = Mock()
    mock.BCM = 11
    mock.IN = 1
    mock.OUT = 2
    mock.PUD_UP = 22
    mock.FALLING = 31
    mock.BOTH = 33
    mock.setup = Mock()
    mock.add_event_detect = Mock()
    mock.cleanup = Mock()
    return mock

@pytest.fixture
def mock_vlc():
    """Provide a mock VLC interface for testing"""
    mock = Mock()
    mock.Instance = Mock(return_value=Mock())
    return mock

@pytest.fixture
def mock_config():
    """Provide test configuration"""
    return {
        'default_stations': ["Test Station 1", "Test Station 2", "Test Station 3"],
        'default_volume': 80,
        'gpio': {
            'rotary': {'clk': 11, 'dt': 9, 'sw': 10},
            'settings': {'debounce_time': 300, 'pull_up': True}
        }
    } 