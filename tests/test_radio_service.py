import pytest
from unittest.mock import Mock, patch, mock_open, MagicMock

try:
    import RPi.GPIO as GPIO
except (RuntimeError, ModuleNotFoundError):
    from tests.mock_gpio import GPIO

from src.app.radio_service import RadioService
from src.player.radio_player import RadioPlayer

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

@patch('src.app.radio_service.GPIOHandler')
@patch('src.app.radio_service.RadioPlayer')
@patch('src.app.radio_service.StreamManager')
def test_radio_service_initialization(mock_stream_manager, mock_radio_player, mock_gpio_handler):
    """Test that RadioService initializes all components correctly"""
    # Setup mocks
    mock_player = Mock()
    mock_gpio = Mock()
    mock_streams = Mock()
    
    # Configure stream manager mock
    mock_streams.get_streams_by_slots.return_value = {
        1: "http://test1.stream",
        2: "http://test2.stream"
    }
    
    # Configure return values
    mock_radio_player.return_value = mock_player
    mock_gpio_handler.return_value = mock_gpio
    mock_stream_manager.return_value = mock_streams
    
    # Create service
    service = RadioService()
    
    # Check components are initialized
    assert service.stream_manager is not None
    assert service.player is not None
    assert service.gpio_handler is not None
    
    # Verify GPIO handler was set up correctly
    mock_gpio_handler.return_value.setup.assert_called_once_with(mock_player, mock_streams)

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

@patch('src.hardware.gpio_handler.GPIO')
def test_radio_service_initialization_sound(mock_gpio):
    """Test that RadioService plays initialization sound"""
    # Reset singleton state
    RadioPlayer._instance = None
    
    # Setup GPIO mock
    mock_gpio.BCM = 11
    mock_gpio.IN = 1
    mock_gpio.FALLING = 2
    mock_gpio.PUD_UP = 22
    mock_gpio.setmode = Mock()
    mock_gpio.setup = Mock()
    mock_gpio.add_event_detect = Mock()
    mock_gpio.cleanup = Mock()

    # Create mocks
    mock_player = MagicMock()
    mock_instance = MagicMock()
    mock_media = MagicMock()
    mock_vlc_player = MagicMock()

    # Configure mock instance
    mock_instance.media_new.return_value = mock_media
    mock_player.instance = mock_instance
    mock_player.player = mock_vlc_player

    # Patch the required components
    with patch('src.player.radio_player.RadioPlayer', autospec=True) as mock_radio_player_class, \
         patch('src.utils.stream_manager.StreamManager') as mock_stream_mgr, \
         patch('src.player.radio_player.vlc') as mock_vlc:
        
        # Configure mocks
        mock_radio_player_instance = mock_player
        mock_radio_player_class.return_value = mock_radio_player_instance
        mock_stream_mgr.return_value.get_streams_by_slots.return_value = {
            1: "http://test1.stream",
            2: "http://test2.stream"
        }
        
        # Configure VLC mock
        mock_vlc.Instance.return_value = mock_instance

        # Create service
        service = RadioService()

        # Verify initialization sound was played
        mock_instance.media_new.assert_any_call("/home/radio/internetRadio/sounds/success.wav")

@patch('src.app.radio_service.GPIOHandler')
@patch('src.app.radio_service.RadioPlayer')
@patch('src.app.radio_service.StreamManager')
def test_radio_service_preload_streams(mock_stream_manager, mock_radio_player, mock_gpio_handler):
    """Test that streams are preloaded during initialization"""
    # Setup mocks
    mock_player = Mock()
    mock_instance = Mock()
    mock_media = Mock()
    
    # Configure mock instance
    mock_instance.media_new.return_value = mock_media
    mock_player.instance = mock_instance
    mock_radio_player.return_value = mock_player
    
    # Configure stream manager mock
    test_streams = {
        1: "http://test1.stream",
        2: "http://test2.stream"
    }
    mock_stream_manager.return_value.get_streams_by_slots.return_value = test_streams
    
    # Configure GPIO handler mock
    mock_gpio_handler.return_value = Mock()
    
    # Create service
    service = RadioService()
    
    # Verify streams were preloaded
    assert mock_instance.media_new.call_count >= len(test_streams)
    for stream in test_streams.values():
        mock_instance.media_new.assert_any_call(stream)
        mock_media.parse.assert_called()