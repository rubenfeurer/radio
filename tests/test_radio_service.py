import pytest
from unittest.mock import Mock, patch, mock_open

try:
    import RPi.GPIO as GPIO
except (RuntimeError, ModuleNotFoundError):
    from tests.mock_gpio import GPIO

from src.app.radio_service import RadioService

@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the singleton instance before each test"""
    RadioService._instance = None
    RadioService._initialized = False
    yield

@pytest.fixture
def mock_stream_manager():
    with patch('src.app.radio_service.StreamManager') as mock:
        manager = Mock()
        manager.get_streams_by_slots.return_value = [
            {"name": "Station1", "url": "url1"},
            {"name": "Station2", "url": "url2"},
            {"name": "Station3", "url": "url3"}
        ]
        mock.return_value = manager
        yield manager

@pytest.fixture
def mock_radio_player():
    with patch('src.app.radio_service.RadioPlayer') as mock:
        player = Mock()
        player.get_status.return_value = {
            "state": "stopped",
            "current_station": None,
            "volume": 80
        }
        mock.return_value = player
        yield player

@pytest.fixture
def mock_gpio_handler():
    with patch('src.app.radio_service.GPIOHandler') as mock_class:
        handler = Mock()
        # Create a setup method as a Mock object, not a function
        handler.setup = Mock()
        
        def side_effect(player, stream_manager):
            handler.player = player
            handler.stream_manager = stream_manager
        
        handler.setup.side_effect = side_effect
        mock_class.return_value = handler
        yield handler

@pytest.fixture(autouse=True)
def mock_gpio():
    with patch('src.hardware.rotary_handler.GPIO') as mock:
        # Setup GPIO mock
        mock.BCM = 11
        mock.IN = 1
        mock.FALLING = 2
        mock.RISING = 3
        mock.BOTH = 4
        mock.PUD_UP = 22
        mock.setmode = Mock()
        mock.setup = Mock()
        mock.add_event_detect = Mock()
        mock.input = Mock()
        yield mock

@pytest.fixture(autouse=True)
def mock_config_for_all():
    """Mock configuration for all tests that need it"""
    config_data = {
        'gpio': {
            'rotary': {
                'clk': 11,
                'dt': 9,
                'sw': 10
            }
        },
        'rotary': {
            'settings': {
                'clockwise_increases': True,
                'debounce_time': 50,
                'double_click_timeout': 500,
                'volume_step': 5
            }
        }
    }
    
    # Mock both the config file and the RotaryHandler
    with patch('tomli.load', return_value=config_data), \
         patch('builtins.open', mock_open()), \
         patch('src.hardware.rotary_handler.open', mock_open()):
        yield config_data

@pytest.fixture
def mock_rotary_handler(mock_config_for_all):
    """Mock RotaryHandler with proper config"""
    with patch('src.app.radio_service.RotaryHandler') as mock:
        handler = Mock()
        mock.return_value = handler
        handler.cleanup = Mock()
        yield handler

def test_radio_service_singleton(mock_stream_manager, mock_radio_player, mock_gpio_handler):
    service1 = RadioService()
    service2 = RadioService()
    assert service1 is service2

def test_radio_service_initialization(mock_stream_manager, mock_radio_player, mock_gpio_handler):
    service = RadioService()
    
    # Check components are initialized
    assert service.stream_manager is not None
    assert service.player is not None
    assert service.gpio_handler is not None
    
    # Check GPIO handler dependencies are set
    mock_gpio_handler.setup.assert_called_once_with(service.player, service.stream_manager)
    
    # Verify dependencies were properly set
    assert mock_gpio_handler.player is service.player
    assert mock_gpio_handler.stream_manager is service.stream_manager

def test_radio_service_cleanup(mock_stream_manager, mock_radio_player, mock_gpio_handler):
    service = RadioService()
    service.cleanup()
    service.player.cleanup.assert_called_once()

def test_radio_service_get_status(mock_stream_manager, mock_radio_player, mock_gpio_handler):
    service = RadioService()
    status = service.get_status()
    assert status == {
        "state": "stopped",
        "current_station": None,
        "volume": 80
    }
    service.player.get_status.assert_called_once()

def test_radio_service_error_handling():
    # Mock RadioPlayer to raise an exception during initialization
    with patch('src.app.radio_service.RadioPlayer') as mock_player:
        mock_player.side_effect = Exception("Test error")
        # Reset singleton state
        RadioService._instance = None
        RadioService._initialized = False
        
        with pytest.raises(Exception) as exc_info:
            RadioService()
        assert "Test error" in str(exc_info.value)