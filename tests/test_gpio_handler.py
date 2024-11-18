import pytest
from unittest.mock import Mock, patch, mock_open, call
import logging
import time
from src.hardware.gpio_handler import GPIOHandler
from src.hardware.button_handler import ButtonPress

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
    player._status = {
        "state": "stopped",
        "current_station": None,
        "volume": 80
    }
    
    def get_status():
        return player._status.copy()
    
    def play(stream):
        player._status.update({
            "state": "playing",
            "current_station": stream
        })
    
    player.get_status = Mock(side_effect=get_status)
    player.play = Mock(side_effect=play)
    player.stop = Mock()
    return player

@pytest.fixture
def mock_stream_manager():
    manager = Mock()
    manager.get_streams_by_slots.return_value = {
        1: {"url": "http://test1.com/stream", "name": "Test Stream 1"},
        2: {"url": "http://test2.com/stream", "name": "Test Stream 2"},
        3: {"url": "http://test3.com/stream", "name": "Test Stream 3"}
    }
    return manager

@pytest.fixture
def gpio_handler(mock_player, mock_stream_manager):
    handler = GPIOHandler()
    handler.setup(mock_player, mock_stream_manager)
    print("\nDEBUG: GPIO handler initialized")
    return handler

@pytest.fixture(autouse=True)
def setup_logging():
    """Configure logging for all tests"""
    logging.basicConfig(level=logging.ERROR)
    yield

def test_button_1_controls_first_slot(gpio_handler, mock_player):
    """Test that button 1 toggles playback of its assigned stream"""
    # Initial state should be stopped
    initial_status = mock_player.get_status()
    assert initial_status["state"] == "stopped"
    assert initial_status["current_station"] is None
    
    # Press button 1 (GPIO 17) - should play first slot
    gpio_handler.button_callback(17)
    mock_player.play.assert_called_with({"url": "http://test1.com/stream", "name": "Test Stream 1"})

def test_gpio_initialization_and_cleanup(gpio_handler, mock_gpio):
    """Test that GPIO is properly initialized and cleaned up"""
    # Verify GPIO setup
    mock_gpio.setmode.assert_called_once_with(mock_gpio.BCM)
    
    # Verify button pins are set up correctly
    expected_pins = [17, 16, 26]  # The default pins from config
    for pin in expected_pins:
        mock_gpio.setup.assert_any_call(pin, mock_gpio.IN, pull_up_down=mock_gpio.PUD_UP)
        mock_gpio.add_event_detect.assert_any_call(
            pin, 
            mock_gpio.FALLING,
            callback=gpio_handler.button_callback,
            bouncetime=300
        )
    
    # Test cleanup
    gpio_handler.cleanup()
    mock_gpio.cleanup.assert_called_once()
    assert GPIOHandler._initialized is False

def test_button_handler_reinitialization(mock_gpio):
    """Test that handler can be reinitialized after cleanup"""
    handler1 = GPIOHandler()
    handler1.cleanup()
    
    # Create new handler
    handler2 = GPIOHandler()
    assert handler2._initialized is False
    
    # Setup should work
    handler2.setup(Mock(), Mock())
    assert handler2._initialized is True

def test_button_press_after_initialization(gpio_handler, mock_player):
    """Test that first button press after initialization works correctly"""
    # Create mock stream manager
    mock_stream_manager = Mock()
    mock_stream_manager.get_streams_by_slots.return_value = {
        1: "http://test1.com/stream",
        2: "http://test2.com/stream",
        3: "http://test3.com/stream"
    }
    
    # Setup GPIO handler with dependencies
    gpio_handler.setup(mock_player, mock_stream_manager)
    
    # Initial state should be stopped
    initial_status = mock_player.get_status()
    assert initial_status["state"] == "stopped"
    
    # First button press after initialization
    gpio_handler.button_callback(17)  # Button 1
    mock_player.play.assert_called_with("http://test1.com/stream")
    
    # Verify state changed
    assert mock_player.get_status()["state"] == "playing"

def test_debounce_functionality(gpio_handler, mock_player, mock_stream_manager):
    """Test that button debouncing works correctly"""
    # Reset the last button press time to ensure debounce doesn't interfere
    gpio_handler.last_button_press = 0
    
    # Create a new Mock for stream_toggler with handle_button_press method
    mock_toggler = Mock()
    mock_toggler.handle_button_press = Mock()
    gpio_handler.stream_toggler = mock_toggler
    
    # First press should work
    gpio_handler.button_callback(17)
    assert mock_toggler.handle_button_press.call_count == 1
    
    # Immediate second press should be ignored due to debounce
    gpio_handler.button_callback(17)
    assert mock_toggler.handle_button_press.call_count == 1
    
    # Wait for debounce time to expire
    time.sleep(0.4)
    
    # Third press should work
    gpio_handler.button_callback(17)
    assert mock_toggler.handle_button_press.call_count == 2

def test_multiple_button_interaction(gpio_handler, mock_player, mock_stream_manager):
    """Test interaction between different buttons"""
    gpio_handler.setup(mock_player, mock_stream_manager)
    
    # Reset debounce time for testing
    gpio_handler.last_button_press = 0
    
    # Create a new Mock for stream_toggler with handle_button_press method
    mock_toggler = Mock()
    mock_toggler.handle_button_press = Mock()
    gpio_handler.stream_toggler = mock_toggler
    
    # Press button 1
    gpio_handler.button_callback(17)
    assert mock_toggler.handle_button_press.call_count == 1
    
    # Reset debounce time before second button press
    gpio_handler.last_button_press = 0
    
    # Press button 2
    gpio_handler.button_callback(16)
    assert mock_toggler.handle_button_press.call_count == 2
    
    # Verify the button presses were handled with correct button indices
    mock_toggler.handle_button_press.assert_has_calls([
        call(ButtonPress(channel=17, button_index=1)),
        call(ButtonPress(channel=16, button_index=2))
    ], any_order=False)

def test_error_handling(gpio_handler, mock_player, mock_stream_manager, caplog):
    """Test error handling in button callback"""
    # Set up logging
    caplog.set_level(logging.ERROR)
    logger = logging.getLogger('src.hardware.gpio_handler')
    logger.setLevel(logging.ERROR)
    
    # Create a mock toggler that raises an exception
    mock_toggler = Mock()
    mock_toggler.handle_button_press = Mock(side_effect=Exception("Test error"))
    gpio_handler.stream_toggler = mock_toggler
    
    # Reset the last button press time
    gpio_handler.last_button_press = 0
    
    # Press button should handle error gracefully
    gpio_handler.button_callback(17)
    
    # Verify error was logged
    assert any("Error in button callback" in record.message for record in caplog.records)

def test_invalid_button_channel(gpio_handler, mock_player, mock_stream_manager, caplog):
    """Test handling of invalid button channel"""
    # Set up logging
    caplog.set_level(logging.ERROR)
    logger = logging.getLogger('src.hardware.gpio_handler')
    logger.setLevel(logging.ERROR)
    
    # Reset the last button press time
    gpio_handler.last_button_press = 0
    
    # Try to trigger callback with invalid channel
    gpio_handler.button_callback(99)
    
    # Check if the error was logged
    assert any("Invalid button channel" in record.message for record in caplog.records)

def test_config_loading(mock_gpio):
    """Test loading of custom button configuration"""
    custom_config = {
        'gpio': {
            'buttons': {
                'button1': 5,
                'button2': 6,
                'button3': 13
            },
            'settings': {
                'debounce_time': 200
            }
        }
    }
    
    with patch('tomli.load', return_value=custom_config), \
         patch('builtins.open', mock_open(read_data=str(custom_config))):
        handler = GPIOHandler()
        handler.setup(Mock(), Mock())
        
        # Verify custom pins were set up
        expected_calls = [
            call(5, mock_gpio.IN, pull_up_down=mock_gpio.PUD_UP),
            call(6, mock_gpio.IN, pull_up_down=mock_gpio.PUD_UP),
            call(13, mock_gpio.IN, pull_up_down=mock_gpio.PUD_UP)
        ]
        assert all(call in mock_gpio.setup.call_args_list for call in expected_calls)