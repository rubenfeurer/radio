import pytest
from unittest.mock import patch, Mock
from src.hardware.audio_player import AudioPlayer


@pytest.mark.asyncio
async def test_audio_player_init():
    """Test audio player initialization"""
    with patch("mpv.MPV") as mock_mpv, patch(
        "subprocess.run"
    ) as mock_run:  # Mock both MPV and amixer
        mock_instance = Mock()
        mock_mpv.return_value = mock_instance
        player = AudioPlayer()
        assert player is not None


@pytest.mark.asyncio
async def test_play_stream():
    """Test playing a stream"""
    with patch("mpv.MPV") as mock_mpv, patch("subprocess.run") as mock_run:
        mock_instance = Mock()
        mock_mpv.return_value = mock_instance
        player = AudioPlayer()
        test_url = "http://test.stream/radio"
        await player.play(test_url)
        mock_instance.play.assert_called_once_with(test_url)


@pytest.mark.asyncio
async def test_stop_stream():
    """Test stopping a stream"""
    with patch("mpv.MPV") as mock_mpv, patch("subprocess.run") as mock_run:
        mock_instance = Mock()
        mock_mpv.return_value = mock_instance
        player = AudioPlayer()
        await player.stop()
        mock_instance.stop.assert_called_once()


@pytest.mark.asyncio
async def test_set_volume():
    """Test setting volume"""
    with patch("mpv.MPV") as mock_mpv, patch("subprocess.run") as mock_run:
        mock_instance = Mock()
        mock_mpv.return_value = mock_instance
        player = AudioPlayer()
        await player.set_volume(50)

        # Verify MPV volume was set
        assert mock_instance.volume == 50

        # Verify amixer was called
        mock_run.assert_called_once()
