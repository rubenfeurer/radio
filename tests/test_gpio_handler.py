import pytest
from unittest.mock import Mock, patch
from src.hardware.gpio_handler import GPIOHandler
import tomli
import os

@pytest.fixture(autouse=True)
def mock_gpio():
    with patch('src.hardware.gpio_handler.GPIO') as mock:
        # Setup GPIO mock
        mock.BCM = 11
        mock.IN = 1
        mock.FALLING = 2
        mock.PUD_UP = 22
        mock.setmode = Mock()
        mock.setup = Mock()
        mock.add_event_detect = Mock()
        mock.input = Mock(return_value=1)
        mock.cleanup = Mock()
        yield mock

@pytest.fixture
def mock_player():
    player = Mock()
    # Default status is stopped
    player.get_status.return_value = {"state": "stopped", "current_station": None, "volume": 80}
    return player

@pytest.fixture
def mock_stream_manager():
    manager = Mock()
    manager.get_streams_by_slots.return_value = [
        {"name": "Test Station 1", "url": "http://test1.com/stream"},
        {"name": "Test Station 2", "url": "http://test2.com/stream"},
        {"name": "Test Station 3", "url": "http://test3.com/stream"}
    ]
    return manager

@pytest.fixture
def mock_config(tmp_path):
    config = {
        "gpio": {
            "button_1_pin": 17,
            "button_2_pin": 16,
            "button_3_pin": 26,
            "settings": {
                "debounce_time": 300,
                "pull_up": True
            }
        }
    }
    config_path = tmp_path / "config.toml"
    
    # Write the config manually instead of using tomli.dump
    with open(config_path, "w") as f:
        f.write("""
[gpio]
button_1_pin = 17
button_2_pin = 16
button_3_pin = 26

[gpio.settings]
debounce_time = 300
pull_up = true
""")
    
    return str(config_path)

@pytest.fixture
def gpio_handler(mock_gpio, mock_player, mock_stream_manager, mock_config):
    handler = GPIOHandler(config_file=mock_config)
    handler.player = mock_player
    handler.stream_manager = mock_stream_manager
    return handler

def test_button_1_controls_first_slot(gpio_handler, mock_player):
    # Press button 1 (GPIO 17) - should play first slot
    gpio_handler.button_callback(17)
    mock_player.play.assert_called_with("http://test1.com/stream")
    
    # Update status to playing
    mock_player.get_status.return_value = {
        "state": "playing",
        "current_station": "http://test1.com/stream",
        "volume": 80
    }
    
    # Press button 1 again - should stop
    gpio_handler.button_callback(17)
    mock_player.stop.assert_called_once()

def test_pressing_different_button_switches_streams(gpio_handler, mock_player):
    # Start playing first slot
    gpio_handler.button_callback(17)  # Button 1
    mock_player.play.assert_called_with("http://test1.com/stream")
    
    # Update status to playing first stream
    mock_player.get_status.return_value = {
        "state": "playing",
        "current_station": "http://test1.com/stream",
        "volume": 80
    }
    mock_player.play.reset_mock()
    
    # Press button 2 (GPIO 16)
    gpio_handler.button_callback(16)
    # Should stop current stream
    mock_player.stop.assert_called_once()
    # Should play second slot
    mock_player.play.assert_called_with("http://test2.com/stream")

def test_each_button_controls_its_slot(gpio_handler, mock_player):
    # Test button 1 (GPIO 17)
    gpio_handler.button_callback(17)
    mock_player.play.assert_called_with("http://test1.com/stream")
    mock_player.play.reset_mock()
    
    # Test button 2 (GPIO 16)
    gpio_handler.button_callback(16)
    mock_player.play.assert_called_with("http://test2.com/stream")
    mock_player.play.reset_mock()
    
    # Test button 3 (GPIO 26)
    gpio_handler.button_callback(26)
    mock_player.play.assert_called_with("http://test3.com/stream")

def test_button_press_starts_playback(gpio_handler, mock_player):
    """Test that pressing a button starts playback when stopped"""
    mock_player.get_status.return_value = {'state': 'stopped', 'current_station': None}
    
    gpio_handler.button_callback(17)  # Button 1
    
    mock_player.play.assert_called_once()
    assert mock_player.play.call_args[0][0] == "http://test1.com/stream"

def test_button_press_stops_playback(gpio_handler, mock_player):
    """Test that pressing a button stops playback when playing"""
    mock_player.get_status.return_value = {
        'state': 'playing',
        'current_station': 'http://test1.com/stream'
    }
    
    gpio_handler.button_callback(17)  # Button 1
    
    mock_player.stop.assert_called_once()

def test_button_press_switches_station(gpio_handler, mock_player):
    """Test that pressing a different button switches stations"""
    mock_player.get_status.return_value = {
        'state': 'playing',
        'current_station': 'http://test1.com/stream'
    }
    
    gpio_handler.button_callback(16)  # Button 2
    
    mock_player.play.assert_called_once()
    assert mock_player.play.call_args[0][0] == "http://test2.com/stream"

# Add new tests for additional coverage
def test_button_press_with_invalid_status(gpio_handler, mock_player):
    """Test handling of invalid player status"""
    mock_player.get_status.return_value = {'state': 'unknown', 'current_station': None}
    
    gpio_handler.button_callback(17)  # Button 1
    
    mock_player.play.assert_called_once()
    assert mock_player.play.call_args[0][0] == "http://test1.com/stream"

def test_button_press_with_missing_streams(gpio_handler, mock_player, mock_stream_manager):
    """Test handling when no streams are available"""
    mock_stream_manager.get_streams_by_slots.return_value = []
    
    gpio_handler.button_callback(17)  # Button 1
    
    mock_player.play.assert_not_called()

def test_button_debounce(gpio_handler, mock_player):
    """Test that rapid button presses are debounced"""
    mock_player.get_status.return_value = {'state': 'stopped', 'current_station': None}