import pytest
from unittest.mock import Mock, patch
from src.hardware.audio_player import AudioPlayer

@pytest.fixture
def audio_player():
    return AudioPlayer()

def test_audio_player_init(audio_player):
    assert audio_player.volume == 70
    assert audio_player.is_playing == False
    assert audio_player.current_url is None

@pytest.mark.asyncio
async def test_play_stream():
    with patch('mpv.MPV') as mock_mpv:
        mock_instance = Mock()
        mock_mpv.return_value = mock_instance
        
        player = AudioPlayer()
        test_url = "http://test.stream/radio"
        
        await player.play(test_url)
        
        mock_instance.play.assert_called_once_with(test_url)
        assert player.is_playing == True
        assert player.current_url == test_url

@pytest.mark.asyncio
async def test_stop_stream():
    with patch('mpv.MPV') as mock_mpv:
        mock_instance = Mock()
        mock_mpv.return_value = mock_instance
        
        player = AudioPlayer()
        await player.stop()
        
        mock_instance.stop.assert_called_once()
        assert player.is_playing == False
        assert player.current_url is None

@pytest.mark.asyncio
async def test_set_volume():
    with patch('mpv.MPV') as mock_mpv:
        mock_instance = Mock()
        mock_mpv.return_value = mock_instance
        
        player = AudioPlayer()
        await player.set_volume(50)
        
        assert player.volume == 50
        assert mock_instance.volume == 50 