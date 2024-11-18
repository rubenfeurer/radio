import pytest
from unittest.mock import Mock, patch
from src.app.radio_service import RadioService
from src.player.radio_player import RadioPlayer
import time

@pytest.mark.integration
def test_audio_pipeline():
    """Test complete audio pipeline from stream to output"""
    with patch('vlc.Instance') as mock_vlc_instance, \
         patch('subprocess.run') as mock_run:
        
        # Setup mocks
        mock_player = Mock()
        mock_media = Mock()
        mock_vlc_instance.return_value.media_player_new.return_value = mock_player
        mock_vlc_instance.return_value.media_new.return_value = mock_media
        
        # Initialize service
        service = RadioService()
        
        # Test volume control
        service.player.set_volume(50)
        mock_run.assert_called()
        
        # Test stream playback
        test_stream = "http://test.stream/audio"
        service.play_stream(test_stream)
        
        # Verify media was created and played
        mock_vlc_instance.return_value.media_new.assert_called_with(test_stream)
        mock_player.set_media.assert_called_with(mock_media)
        mock_player.play.assert_called()
        
        # Verify status
        status = service.get_status()
        assert status["state"] == "playing"
        assert status["current_station"] == test_stream
        assert status["volume"] == 50 