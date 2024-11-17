import pytest
from unittest.mock import Mock, patch, MagicMock
from src.player.radio_player import RadioPlayer

@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the singleton instance before each test"""
    RadioPlayer._instance = None
    RadioPlayer._initialized = False
    yield

@pytest.fixture
def mock_subprocess():
    with patch('subprocess.run') as mock:
        mock.return_value = MagicMock(returncode=0, stdout="", stderr="")
        yield mock

@patch('src.player.radio_player.vlc')
def test_radio_player_singleton(mock_vlc):
    # Setup mock VLC instance
    mock_instance = MagicMock()
    mock_vlc.Instance.return_value = mock_instance
    mock_instance.media_player_new.return_value = MagicMock()
    
    player1 = RadioPlayer()
    player2 = RadioPlayer()
    assert player1 is player2

@patch('src.player.radio_player.vlc')
@patch('subprocess.run')
def test_play_stop(mock_subprocess, mock_vlc):
    # Reset singleton state
    RadioPlayer._instance = None
    
    # Setup mock VLC instance
    mock_player = MagicMock()
    mock_media = MagicMock()
    mock_instance = MagicMock()
    
    # Configure VLC mocks
    mock_vlc.Instance.return_value = mock_instance
    mock_instance.media_player_new.return_value = mock_player
    mock_instance.media_new.return_value = mock_media
    
    # Configure subprocess mock
    mock_subprocess.return_value = MagicMock(returncode=0, stdout="", stderr="")
    
    # Create player
    player = RadioPlayer()
    
    # Test play
    test_url = "http://test.stream/url"
    player.play(test_url)
    
    # Verify media was created and played
    mock_instance.media_new.assert_called_once_with(test_url)
    mock_player.set_media.assert_called_once_with(mock_media)
    mock_player.play.assert_called_once()
    
    # Test stop
    player.stop()
    mock_player.stop.assert_called_once()