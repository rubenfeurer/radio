import pytest
from unittest.mock import Mock, patch
import os
from src.utils.sound_player import SoundPlayer

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
def test_play_sound_success(mock_vlc_instance):
    """Test playing a sound file that exists"""
    # Setup mock
    mock_player = Mock()
    mock_instance = Mock()
    mock_instance.media_player_new.return_value = mock_player
    mock_vlc_instance.return_value = mock_instance
    
    # Create player with mocked instance
    player = SoundPlayer()
    player.instance = mock_instance
    player.player = mock_player
    
    # Test sound playing
    test_sound = "success.wav"
    test_path = os.path.join(player.sound_dir, test_sound)
    
    # Create test file if it doesn't exist
    if not os.path.exists(player.sound_dir):
        os.makedirs(player.sound_dir)
    if not os.path.exists(test_path):
        with open(test_path, 'w') as f:
            f.write('test')
    
    player.play_sound(test_sound, wait=False)
    mock_player.play.assert_called_once()

def test_play_sound_file_not_found():
    """Test playing a non-existent sound file"""
    player = SoundPlayer()
    with patch('logging.Logger.error') as mock_logger:
        player.play_sound("nonexistent.wav")
        mock_logger.assert_called_once() 