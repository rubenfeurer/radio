import pytest
from unittest.mock import Mock, patch, MagicMock
from src.hardware.gpio_handler import GPIOHandler
from src.player.radio_player import RadioPlayer

@pytest.fixture
def mock_gpio():
    with patch('RPi.GPIO') as mock:
        yield mock

@pytest.fixture
def mock_radio_player():
    with patch('src.player.radio_player.RadioPlayer') as mock:
        yield mock

@patch('src.hardware.gpio_handler.GPIO')
def test_gpio_initialization(mock_gpio):
    # Mock the GPIO module attributes
    mock_gpio.BCM = 11  # BCM mode value
    mock_gpio.IN = 1    # Input mode value
    mock_gpio.FALLING = 2  # Falling edge value
    mock_gpio.PUD_UP = 22  # Pull-up value
    
    # Create handler
    handler = GPIOHandler()
    
    # Verify GPIO mode was set to BCM
    mock_gpio.setmode.assert_called_once_with(mock_gpio.BCM)
    
    # Verify setup was called for each pin
    assert mock_gpio.setup.call_count == 3
    
    # Verify each pin setup
    expected_pins = [17, 16, 26]  # GPIO pins from GPIOHandler
    for pin in expected_pins:
        mock_gpio.setup.assert_any_call(
            pin, 
            mock_gpio.IN, 
            pull_up_down=mock_gpio.PUD_UP
        )
    
    # Verify event detection was added for each pin
    assert mock_gpio.add_event_detect.call_count == 3
    for pin in expected_pins:
        mock_gpio.add_event_detect.assert_any_call(
            pin,
            mock_gpio.FALLING,
            callback=handler.button_callback,
            bouncetime=300
        )

@patch('src.hardware.gpio_handler.GPIO')
def test_button_callback(mock_gpio):
    # Create mock player with proper status structure
    mock_player = MagicMock()
    mock_player.get_status = MagicMock(return_value={"state": "stopped", "current_station": None})
    
    # Create mock state manager with proper return structure
    mock_state_manager = MagicMock()
    mock_stations = [
        {"name": "Station1", "url": "url1"},
        {"name": "Station2", "url": "url2"},
        {"name": "Station3", "url": "url3"}
    ]
    mock_state_manager.get_selected_stations.return_value = mock_stations
    
    # Create handler
    handler = GPIOHandler()
    
    # Replace dependencies with mocks
    handler.player = mock_player
    handler.state_manager = mock_state_manager
    
    # Test button press when stopped
    handler.button_callback(17)
    mock_player.play.assert_called_once_with("url1")
    
    # Change status to playing same station
    mock_player.get_status.return_value = {
        "state": "playing",
        "current_station": "url1"
    }
    
    # Test button press when playing - should stop
    handler.button_callback(17)
    mock_player.stop.assert_called_once()