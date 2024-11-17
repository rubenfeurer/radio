import pytest
from unittest.mock import Mock, patch
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
    with patch('src.app.radio_service.GPIOHandler') as mock:
        handler = Mock()
        mock.return_value = handler
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
    assert service.gpio_handler.player == service.player
    assert service.gpio_handler.stream_manager == service.stream_manager

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