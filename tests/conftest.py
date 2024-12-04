import os
import pytest
from unittest.mock import MagicMock

@pytest.fixture(autouse=True)
def mock_hardware():
    """Mock hardware components when MOCK_HARDWARE is set"""
    if os.getenv("MOCK_HARDWARE") == "true":
        # Mock pigpio
        mock_pi = MagicMock()
        mock_pi.connected = True
        
        # Patch the pigpio import
        import sys
        sys.modules['pigpio'] = MagicMock()
        sys.modules['pigpio'].pi.return_value = mock_pi
        
        # Mock MPV
        sys.modules['mpv'] = MagicMock()
        
        yield mock_pi
    else:
        yield None 