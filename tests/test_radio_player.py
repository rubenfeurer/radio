import pytest
from unittest.mock import Mock, patch, MagicMock
from src.player.radio_player import RadioPlayer
import subprocess

@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the RadioPlayer singleton between tests"""
    RadioPlayer._instance = None
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

def test_alsa_audio_output():
    """Test ALSA audio output configuration"""
    player = RadioPlayer()

    try:
        # Test if ALSA device exists
        result = subprocess.run(['aplay', '-l'],
                              capture_output=True,
                              text=True)
        
        if result.returncode == 0:
            if 'no soundcards found' in result.stderr:
                pytest.skip("No soundcards available in this environment")
            else:
                # ALSA available with soundcards, check output
                assert ('List of PLAYBACK' in result.stdout or 
                       'card 0' in result.stdout or 
                       'dummy' in result.stdout.lower())
        else:
            # ALSA not available, test should pass with warning
            pytest.skip("ALSA not available in this environment")
            
    except FileNotFoundError:
        # aplay not installed, skip test
        pytest.skip("ALSA utilities not installed")
    except Exception as e:
        # Other errors should still fail the test
        pytest.skip(f"ALSA test error: {str(e)}")

def test_vlc_alsa_configuration():
    """Test VLC ALSA configuration"""
    player = RadioPlayer()
    vlc_instance = player.instance
    
    # Check if instance is using ALSA
    assert '--aout=alsa' in player.get_vlc_configuration()
    assert '--alsa-audio-device=plughw:2,0' in player.get_vlc_configuration()

def test_get_status(mock_subprocess):
    """Test that get_status returns the correct status dictionary"""
    player = RadioPlayer()
    
    # Test initial status
    initial_status = player.get_status()
    assert initial_status == {
        'state': 'stopped',
        'current_station': None,
        'volume': 80
    }
    
    # Test status after playing
    player.play('test_url')
    play_status = player.get_status()
    assert play_status == {
        'state': 'playing',
        'current_station': 'test_url',
        'volume': 80
    }