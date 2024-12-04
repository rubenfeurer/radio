import pytest
import os
from unittest.mock import patch, Mock
from src.hardware.audio_player import AudioPlayer

@pytest.mark.asyncio
async def test_audio_player_init(mock_hardware):
    """Test audio player initialization"""
    if os.getenv("GITHUB_ACTIONS") or os.getenv("MOCK_HARDWARE"):
        player = AudioPlayer()
        assert player is not None
    else:
        with patch('mpv.MPV') as mock_mpv:
            mock_instance = Mock()
            mock_mpv.return_value = mock_instance
            player = AudioPlayer()
            assert player is not None

@pytest.mark.asyncio
async def test_play_stream(mock_hardware):
    """Test playing a stream"""
    if os.getenv("GITHUB_ACTIONS") or os.getenv("MOCK_HARDWARE"):
        player = AudioPlayer()
        test_url = "http://test.stream/radio"
        await player.play(test_url)
        mock_hardware['mpv'].play.assert_called_once_with(test_url)
    else:
        with patch('mpv.MPV') as mock_mpv:
            mock_instance = Mock()
            mock_mpv.return_value = mock_instance
            player = AudioPlayer()
            test_url = "http://test.stream/radio"
            await player.play(test_url)
            mock_instance.play.assert_called_once_with(test_url)

@pytest.mark.asyncio
async def test_stop_stream(mock_hardware):
    """Test stopping a stream"""
    if os.getenv("GITHUB_ACTIONS") or os.getenv("MOCK_HARDWARE"):
        player = AudioPlayer()
        await player.stop()
        mock_hardware['mpv'].stop.assert_called_once()
    else:
        with patch('mpv.MPV') as mock_mpv:
            mock_instance = Mock()
            mock_mpv.return_value = mock_instance
            player = AudioPlayer()
            await player.stop()
            mock_instance.stop.assert_called_once()

@pytest.mark.asyncio
async def test_set_volume(mock_hardware):
    """Test setting volume"""
    if os.getenv("GITHUB_ACTIONS") or os.getenv("MOCK_HARDWARE"):
        player = AudioPlayer()
        await player.set_volume(50)
        assert mock_hardware['mpv'].volume == 50
    else:
        with patch('mpv.MPV') as mock_mpv:
            mock_instance = Mock()
            mock_mpv.return_value = mock_instance
            player = AudioPlayer()
            await player.set_volume(50)
            assert mock_instance.volume == 50