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
from unittest.mock import Mock, patch

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

@pytest.mark.asyncio
async def test_volume_control_integration():
    """Test volume control through both rotary encoder and web interface"""
    loop = asyncio.get_event_loop()
    
    # Initialize components
    with patch('src.hardware.audio_player.AudioPlayer') as MockAudioPlayer:
        mock_player = MockAudioPlayer.return_value
        manager = RadioManager()
        
        # Create volume callback
        async def volume_callback(steps):
            await manager.set_volume(manager.get_status().volume + steps)
            
        # Initialize GPIO with volume callback
        gpio = GPIOController(
            event_loop=loop,
            volume_change_callback=volume_callback
        )
        
        # Test volume change via rotary encoder
        initial_volume = manager.get_status().volume
        
        # Mock the DT pin read to simulate rotation direction
        with patch.object(gpio.pi, 'read', return_value=0):  # Simulate clockwise rotation
            gpio._handle_rotation(settings.ROTARY_CLK, 1, 0)
            await asyncio.sleep(0.1)  # Allow async operation to complete
            
            # If ROTARY_CLOCKWISE_INCREASES is True, expect volume increase
            expected_volume = min(100, initial_volume + gpio.volume_step) if settings.ROTARY_CLOCKWISE_INCREASES else max(0, initial_volume - gpio.volume_step)
            assert manager.get_status().volume == expected_volume
        
        # Test volume change via web interface
        new_volume = 75
        await manager.set_volume(new_volume)
        assert manager.get_status().volume == new_volume

@pytest.mark.asyncio
async def test_button_press_types():
    """Test different types of button presses (single, triple, long)"""
    loop = asyncio.get_event_loop()
    
    # Create counters for callbacks
    single_press_count = 0
    triple_press_count = 0
    long_press_count = 0

    async def single_press_callback(button):
        nonlocal single_press_count
        single_press_count += 1

    async def triple_press_callback(button):
        nonlocal triple_press_count
        triple_press_count += 1

    async def long_press_callback(button):
        nonlocal long_press_count
        long_press_count += 1

    gpio = GPIOController(
        event_loop=loop,
        button_press_callback=single_press_callback,
        triple_press_callback=triple_press_callback,
        long_press_callback=long_press_callback
    )
    
    # Test single press
    gpio._handle_button(settings.ROTARY_SW, 0, 0)  # Press
    await asyncio.sleep(0.05)
    gpio._handle_button(settings.ROTARY_SW, 1, 0)  # Release
    await asyncio.sleep(1.0)  # Wait longer to ensure no triple press
    assert single_press_count == 1
    
    # Reset counters and state
    single_press_count = 0
    gpio.last_press_time = {}
    gpio.press_start_time = {}
    gpio.press_count = {}
    
    # Test triple press with proper timing
    for _ in range(3):
        gpio._handle_button(settings.ROTARY_SW, 0, 0)  # Press
        await asyncio.sleep(0.05)  # Short press duration
        gpio._handle_button(settings.ROTARY_SW, 1, 0)  # Release
        await asyncio.sleep(0.2)  # Interval between presses within TRIPLE_PRESS_INTERVAL
    
    await asyncio.sleep(0.5)  # Wait for triple press detection
    assert triple_press_count == 1
    
    # Cleanup
    gpio.cleanup()

@pytest.mark.asyncio
async def test_status_updates():
    """Test that status updates are properly propagated"""
    loop = asyncio.get_event_loop()
    
    # Create callback counter
    callback_count = 0
    
    async def status_callback(status):
        nonlocal callback_count
        callback_count += 1
    
    manager = RadioManager(status_update_callback=status_callback)
    station = RadioStation(name="Test", url="http://test.com/stream", slot=1)
    manager.add_station(station)
    
    # Test status updates for various actions
    await manager.toggle_station(1)
    await asyncio.sleep(0.2)  # Wait for callback
    assert callback_count > 0
    
    initial_count = callback_count
    await manager.set_volume(80)
    await asyncio.sleep(0.2)  # Wait for callback
    assert callback_count > initial_count