from unittest.mock import Mock, patch

import pytest

from src.hardware.audio_player import AudioPlayer


@pytest.mark.asyncio
async def test_init():
    """Test AudioPlayer initialization"""
    with patch("mpv.MPV") as mock_mpv, patch("subprocess.run") as mock_subprocess:
        mock_instance = Mock()
        mock_mpv.return_value = mock_instance

        AudioPlayer()

        # Use mock_subprocess instead of mock_run
        mock_subprocess.assert_called_once()
        assert mock_mpv.called


@pytest.mark.asyncio
async def test_play_stream():
    """Test playing a stream"""
    with patch("mpv.MPV") as mock_mpv, patch("subprocess.run") as mock_subprocess:
        mock_instance = Mock()
        mock_mpv.return_value = mock_instance

        player = AudioPlayer()
        await player.play_stream("http://test.stream")

        # Verify amixer was called
        mock_subprocess.assert_called_once()

        # Verify MPV was started with correct URL
        mock_instance.play.assert_called_once_with("http://test.stream")


@pytest.mark.asyncio
async def test_stop_stream():
    """Test stopping a stream"""
    with patch("mpv.MPV") as mock_mpv, patch("subprocess.run") as mock_subprocess:
        mock_instance = Mock()
        mock_mpv.return_value = mock_instance

        player = AudioPlayer()
        await player.stop_stream()

        # Verify amixer was called
        mock_subprocess.assert_called_once()

        # Verify MPV was stopped
        mock_instance.stop.assert_called_once()


@pytest.mark.asyncio
async def test_set_volume():
    """Test setting volume"""
    with patch("mpv.MPV") as mock_mpv, patch("subprocess.run") as mock_subprocess:
        mock_instance = Mock()
        mock_mpv.return_value = mock_instance

        player = AudioPlayer()
        await player.set_volume(50)

        # Verify MPV volume was set
        assert mock_instance.volume == 50

        # Verify amixer was called
        mock_subprocess.assert_called_once()
