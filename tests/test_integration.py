import pytest
from unittest.mock import Mock, patch, MagicMock
from src.app.radio_service import RadioService

@pytest.mark.integration
def test_audio_pipeline():
    """Test complete audio pipeline from stream to output"""
    # Create GPIO mock
    gpio_mock = MagicMock()
    gpio_mock.IN = "IN"
    gpio_mock.OUT = "OUT"
    gpio_mock.PUD_UP = "PUD_UP"
    gpio_mock.FALLING = "FALLING"
    gpio_mock.setup = Mock()
    gpio_mock.add_event_detect = Mock()

    # Mock the stream that should be played
    test_stream = {"url": "http://test.stream/audio", "name": "Test Stream"}
    
    with patch('RPi.GPIO', gpio_mock), \
         patch('src.hardware.rotary_handler.GPIO', gpio_mock), \
         patch('src.hardware.gpio_handler.GPIO', gpio_mock), \
         patch('src.utils.stream_manager.StreamManager.get_streams_by_slots', return_value={1: test_stream}), \
         patch('src.utils.sound_player.SoundPlayer.play_sound') as mock_play_sound:

        # Initialize service
        service = RadioService()

        # Get the callback for button 1
        button_callback = None
        for args, kwargs in gpio_mock.add_event_detect.call_args_list:
            if args[0] == 17:  # GPIO 17 is button 1
                button_callback = kwargs.get('callback')
                break
        
        assert button_callback is not None, "Button callback was not registered"

        # Simulate button press
        button_callback(17)

        # Verify the service state
        status = service.get_status()
        assert status["state"] in ["playing", "stopped"], f"Unexpected state: {status['state']}"
        
        # Print debug information
        print("\nDebug Information:")
        print(f"Service Status: {status}")
        print(f"Mock Sound Player Calls: {mock_play_sound.call_args_list}")