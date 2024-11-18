import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock hardware modules
mock_gpio = MagicMock()
sys.modules['RPi.GPIO'] = mock_gpio
sys.modules['RPi'] = MagicMock()
sys.modules['RPi'].GPIO = mock_gpio

@pytest.fixture(autouse=True)
def mock_hardware():
    """Mock hardware components for all tests"""
    with patch('RPi.GPIO', mock_gpio), \
         patch('vlc.Instance') as mock_vlc:
        
        # Configure GPIO mock
        mock_gpio.setmode = MagicMock()
        mock_gpio.setup = MagicMock()
        mock_gpio.IN = MagicMock()
        mock_gpio.OUT = MagicMock()
        mock_gpio.PUD_UP = MagicMock()
        mock_gpio.BCM = MagicMock()
        
        yield {
            'gpio': mock_gpio,
            'vlc': mock_vlc
        }

@pytest.fixture
def client():
    from src.app.routes import app
    app.config['TESTING'] = True
    return app.test_client()