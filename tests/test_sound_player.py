import pytest
from unittest.mock import Mock, patch
import os
import tempfile
import shutil
from src.utils.sound_player import SoundPlayer

@pytest.fixture
def temp_sound_dir():
    """Create a temporary directory for sound files"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir

@pytest.fixture
def sound_player():
    return SoundPlayer()

def test_sound_player_initialization():
    """Test that SoundPlayer initializes correctly"""
    player = SoundPlayer()
    assert player.sound_dir == "/home/radio/internetRadio/sounds"
    assert player.instance is not None
    assert player.player is not None

@patch('vlc.Instance')
def test_play_sound_success(mock_vlc_instance, temp_sound_dir):
    """Test playing a sound file that exists"""
    # Setup mock
    mock_player = Mock()
    mock_instance = Mock()
    mock_instance.media_player_new.return_value = mock_player
    mock_vlc_instance.return_value = mock_instance
    
    # Create player with mocked instance and temporary directory
    player = SoundPlayer()
    player.sound_dir = temp_sound_dir  # Override the default path
    player.instance = mock_instance
    player.player = mock_player
    
    # Create test sound file
    test_sound = "success.wav"
    test_path = os.path.join(temp_sound_dir, test_sound)
    with open(test_path, 'wb') as f:
        f.write(b'dummy audio data')
    
    # Test sound playing
    player.play_sound(test_sound, wait=False)
    
    # Verify media was created and played
    mock_instance.media_new.assert_called_once_with(test_path)
    mock_player.play.assert_called_once()

def test_play_sound_file_not_found():
    """Test playing a non-existent sound file"""
    player = SoundPlayer()
    with patch('logging.Logger.error') as mock_logger:
        player.play_sound("nonexistent.wav")
        mock_logger.assert_called_once() 