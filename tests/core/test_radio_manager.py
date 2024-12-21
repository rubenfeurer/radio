import pytest
from src.core.radio_manager import RadioManager
from src.core.models import RadioStation, SystemStatus
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio
from config.config import settings
import httpx

"""
Test suite for RadioManager class.
Tests core functionality of radio station management and playback control.

Key areas tested:
- Station management (add/remove/get)
- Playback control (play/stop/toggle)
- Volume control and persistence
- State management
- Default station handling
"""

@pytest.fixture
def mock_station_manager():
    """Mock StationManager for testing RadioManager"""
    with patch('src.core.station_manager.StationManager') as mock:
        manager = mock.return_value
        manager.get_station.return_value = RadioStation(
            name="Test Station",
            url="http://test.com",
            slot=1
        )
        yield manager

@pytest.fixture
def radio_manager(mock_station_manager):
    """RadioManager with mocked dependencies"""
    return RadioManager()

@pytest.mark.asyncio
async def test_play_station_with_status_update(radio_manager):
    """Test playing station updates status and broadcasts"""
    # Setup
    callback_called = False
    async def status_callback(status):
        nonlocal callback_called
        callback_called = True
    
    radio_manager._status_update_callback = status_callback
    
    # Test
    await radio_manager.play_station(1)
    
    # Verify
    status = radio_manager.get_status()
    assert status.is_playing == True
    assert status.current_station == 1
    assert callback_called == True

@pytest.mark.asyncio
async def test_toggle_station_behavior(radio_manager):
    """Test complete toggle station behavior"""
    # First toggle - should start playing
    result = await radio_manager.toggle_station(1)
    assert result == True
    assert radio_manager.get_status().is_playing == True
    assert radio_manager.get_status().current_station == 1
    
    # Second toggle - should stop
    result = await radio_manager.toggle_station(1)
    assert result == False
    assert radio_manager.get_status().is_playing == False
    assert radio_manager.get_status().current_station is None

@pytest.mark.asyncio
async def test_volume_change_callback(radio_manager):
    """Test volume change from hardware triggers callback"""
    # Setup
    callback_called = False
    async def status_callback(status):
        nonlocal callback_called
        callback_called = True
    
    radio_manager._status_update_callback = status_callback
    
    # Mock the volume control
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        
        # Test
        await radio_manager._handle_volume_change(5)
        
        # Verify
        assert radio_manager.get_status().volume == settings.DEFAULT_VOLUME + 5
        assert callback_called

@pytest.mark.asyncio
async def test_concurrent_station_toggle(radio_manager):
    """Test concurrent station toggle operations"""
    # Start multiple concurrent toggles
    tasks = [
        radio_manager.toggle_station(1),
        radio_manager.toggle_station(2),
        radio_manager.toggle_station(3)
    ]
    
    # Wait for all to complete
    await asyncio.gather(*tasks)
    
    # Verify only one station is playing
    status = radio_manager.get_status()
    assert status.is_playing
    assert status.current_station is not None

@pytest.mark.asyncio
async def test_long_press_rotary_switch(radio_manager):
    """Test long press on rotary switch triggers mode toggle"""
    # Mock httpx.AsyncClient
    mock_response = MagicMock()
    mock_response.status_code = 200
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )
        
        # Test long press on rotary switch
        await radio_manager._handle_long_press(settings.ROTARY_SW)
        
        # Verify mode toggle endpoint was called
        mock_client.return_value.__aenter__.return_value.post.assert_called_once_with(
            'http://localhost:80/api/v1/mode/toggle'
        )

@pytest.mark.asyncio
async def test_long_press_other_button(radio_manager):
    """Test long press on non-rotary buttons doesn't trigger mode toggle"""
    with patch('httpx.AsyncClient') as mock_client:
        # Test long press on button 1
        await radio_manager._handle_long_press(1)
        
        # Verify mode toggle endpoint was not called
        mock_client.return_value.__aenter__.return_value.post.assert_not_called()

@pytest.mark.asyncio
async def test_long_press_failed_toggle(radio_manager):
    """Test handling of failed mode toggle"""
    # Mock failed response
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )
        
        # Test long press with failed response
        await radio_manager._handle_long_press(settings.ROTARY_SW)
        
        # Verify error was handled gracefully
        mock_client.return_value.__aenter__.return_value.post.assert_called_once_with(
            'http://localhost:80/api/v1/mode/toggle'
        )

@pytest.mark.asyncio
async def test_long_press_network_error(radio_manager):
    """Test handling of network error during mode toggle"""
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            side_effect=httpx.NetworkError("Connection failed")
        )
        
        # Test long press with network error
        await radio_manager._handle_long_press(settings.ROTARY_SW)
        
        # Verify error was handled gracefully
        mock_client.return_value.__aenter__.return_value.post.assert_called_once_with(
            'http://localhost:80/api/v1/mode/toggle'
        )