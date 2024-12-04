"""
Integration test suite for system-wide functionality.
"""
import pytest
from src.hardware.gpio_controller import GPIOController
from src.core.radio_manager import RadioManager
from src.hardware.audio_player import AudioPlayer
from src.core.models import RadioStation
from config.config import settings

@pytest.mark.asyncio
async def test_button_to_audio():
    """Test button press to audio playback flow"""
    gpio = GPIOController()
    manager = RadioManager()
    player = AudioPlayer()
    
    # Add a test station
    station = RadioStation(name="Test", url="http://test.com/stream", slot=1)
    manager.add_station(station)
    
    # Call the callback directly
    gpio._handle_button(settings.BUTTON_PIN_1, 0, 0)  # pin, level, tick
    
    # Wait for any async operations
    await manager.toggle_station(1)
    assert manager.is_playing
    assert manager.current_slot == 1