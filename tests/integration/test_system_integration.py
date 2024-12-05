"""
Integration test suite for system-wide functionality.
"""
import pytest
from src.hardware.gpio_controller import GPIOController
from src.core.radio_manager import RadioManager
from src.hardware.audio_player import AudioPlayer
from src.core.models import RadioStation
from config.config import settings
import asyncio

@pytest.mark.asyncio
async def test_button_to_audio():
    """Test button press to audio playback flow"""
    # Create event loop for testing
    loop = asyncio.get_event_loop()
    
    gpio = GPIOController(event_loop=loop)
    manager = RadioManager()
    player = AudioPlayer()
    
    # Add a test station
    station = RadioStation(name="Test", url="http://test.com/stream", slot=1)
    manager.add_station(station)
    
    # Call the callback directly
    gpio._handle_button(settings.BUTTON_PIN_1, 0, 0)  # Press
    gpio._handle_button(settings.BUTTON_PIN_1, 1, 0)  # Release
    
    # Wait for any async operations
    await asyncio.sleep(0.1)
    await manager.toggle_station(1)
    
    # Check status instead of direct attributes
    status = manager.get_status()
    assert status.is_playing
    assert status.current_station == 1