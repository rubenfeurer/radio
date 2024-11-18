import pytest
from unittest.mock import Mock, patch
import sys

# Use mock GPIO if not on Raspberry Pi
try:
    import RPi.GPIO as GPIO
except (RuntimeError, ModuleNotFoundError):
    from tests.mock_gpio import GPIO

from src.hardware.gpio_handler import GPIOHandler
import time

@pytest.fixture(autouse=True)
def mock_gpio():
    with patch('src.hardware.gpio_handler.GPIO') as mock:
        mock.BCM = 11
        mock.IN = 1
        mock.FALLING = 2
        mock.PUD_UP = 22
        mock.setmode = Mock()
        mock.setup = Mock()
        mock.add_event_detect = Mock()
        mock.cleanup = Mock()
        yield mock

@pytest.fixture
def mock_player():
    player = Mock()
    
    # Initialize status dictionary
    player._status = {
        "state": "stopped",
        "current_station": None,
        "volume": 80
    }
    
    # Create get_status method that returns a copy
    def get_status():
        print(f"DEBUG: get_status called, returning: {player._status}")
        return player._status.copy()
    
    # Create stop method that updates status
    def stop():
        print("DEBUG: stop() called")
        player._status.update({
            "state": "stopped",
            "current_station": None
        })
    
    # Create play method that updates status
    def play(stream):
        print(f"DEBUG: play() called with {stream}")
        player._status.update({
            "state": "playing",
            "current_station": stream
        })
    
    player.get_status = Mock(side_effect=get_status)
    player.stop = Mock(side_effect=stop)
    player.play = Mock(side_effect=play)
    return player

@pytest.fixture
def mock_stream_manager():
    manager = Mock()
    streams = {
        1: "http://test1.com/stream",
        2: "http://test2.com/stream",
        3: "http://test3.com/stream"
    }
    manager.get_streams_by_slots = Mock(return_value=streams)
    return manager

@pytest.fixture
def gpio_handler(mock_player, mock_stream_manager):
    handler = GPIOHandler()
    handler.setup(mock_player, mock_stream_manager)
    print("\nDEBUG: GPIO handler initialized")
    return handler

def test_button_1_controls_first_slot(gpio_handler, mock_player):
    """Test that button 1 toggles playback of its assigned stream"""
    # Initial state should be stopped
    initial_status = mock_player.get_status()
    print("\nDEBUG: Initial status:", initial_status)
    assert initial_status["state"] == "stopped"
    assert initial_status["current_station"] is None
    
    print("\nDEBUG: === First button press ===")
    # Press button 1 (GPIO 17) - should play first slot
    gpio_handler.button_callback(17)
    mock_player.play.assert_called_with("http://test1.com/stream")
    
    # Verify first press state
    first_press_status = mock_player.get_status()
    print("DEBUG: Status after first press:", first_press_status)
    assert first_press_status["state"] == "playing"
    assert first_press_status["current_station"] == "http://test1.com/stream"
    
    # Reset mocks but preserve state
    mock_player.stop.reset_mock()
    mock_player.play.reset_mock()
    
    # Wait for debounce
    time.sleep(0.4)
    
    print("\nDEBUG: === Second button press ===")
    print("DEBUG: Current status before second press:", mock_player.get_status())
    
    # Press button 1 again - should stop
    gpio_handler.button_callback(17)
    
    # Get final status
    final_status = mock_player.get_status()
    print("DEBUG: Status after second press:", final_status)
    print("DEBUG: stop.call_count =", mock_player.stop.call_count)
    print("DEBUG: play.call_count =", mock_player.play.call_count)
    
    # Verify stop was called and play wasn't
    mock_player.stop.assert_called_once()
    mock_player.play.assert_not_called()
    assert final_status["state"] == "stopped"
    assert final_status["current_station"] is None