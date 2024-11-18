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
def mock_aplay_output():
    """Mock aplay -l output"""
    return """
**** List of PLAYBACK Hardware Devices ****
card 0: vc4hdmi0 [vc4-hdmi-0], device 0: MAI PCM i2s-hifi-0 []
card 1: vc4hdmi1 [vc4-hdmi-1], device 0: MAI PCM i2s-hifi-0 []
card 2: Headphones [bcm2835 Headphones], device 0: bcm2835 Headphones []
    """

@pytest.fixture
def mock_amixer_output():
    """Mock amixer output"""
    return """Simple mixer control 'PCM',0
  Capabilities: pvolume
  Playback channels: Front Left - Front Right
  Limits: Playback -10239 - 400
  Mono: Playback -1024 [75%] [-10.24dB]
"""

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
    mock_state = MagicMock()
    
    # Configure VLC state mock
    mock_state.value = 3  # Playing state (3 = playing, 4 = paused)
    mock_player.get_state.return_value = mock_state
    
    # Configure VLC mocks
    mock_vlc.Instance.return_value = mock_instance
    mock_instance.media_player_new.return_value = mock_player
    mock_instance.media_new.return_value = mock_media
    
    # Configure player mock behavior
    mock_player.is_playing.return_value = True
    mock_player.play.return_value = 0  # Success
    
    # Create player
    player = RadioPlayer()
    
    # Reset mock call counts after initialization
    mock_player.stop.reset_mock()
    mock_player.play.reset_mock()
    
    # Test play
    test_url = "http://test.stream/url"
    player.play(test_url)
    
    # Verify play was called
    mock_player.play.assert_called_once()
    
    # Test stop
    player.stop()
    
    # Verify stop was called at least once
    assert mock_player.stop.call_count >= 1
    
    # Verify final state
    assert player.get_status()['state'] == 'stopped'
    assert player.get_status()['current_station'] is None

def test_audio_device_detection(mock_aplay_output):
    """Test audio device detection"""
    with patch('subprocess.run') as mock_run:
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = mock_aplay_output
        mock_run.return_value = mock_result

        player = RadioPlayer()
        assert player.audio_card == '2'

def test_audio_device_detection_fallback(mock_aplay_output):
    """Test audio device detection fallback"""
    with patch('subprocess.run') as mock_run:
        mock_result = Mock()
        mock_result.returncode = 1  # Simulate failure
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        player = RadioPlayer()
        assert player.audio_card == 'default'

def test_volume_control_success():
    """Test successful volume control"""
    with patch('subprocess.run') as mock_run:
        # Configure mock
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        player = RadioPlayer()
        assert player.set_volume(75) == True

        # Verify that one of the valid command formats was called
        assert any([
            call(['amixer', '-c', '2', 'sset', 'PCM', '75%'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) == c
            or
            call(['amixer', 'sset', '-c', '2', 'PCM', '75%'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) == c
            for c in mock_run.call_args_list
        ]), "Neither expected amixer command format was called"

def test_volume_control_failure():
    """Test volume control failure handling"""
    with patch('subprocess.run') as mock_run:
        # Configure mock to fail for all commands
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Error: Invalid command"
        mock_run.return_value = mock_result

        player = RadioPlayer()
        assert player.set_volume(50) == False

def test_get_volume_success(mock_amixer_output):
    """Test successful volume retrieval"""
    with patch('subprocess.run') as mock_run, \
         patch('toml.load') as mock_toml:
        # Mock config
        mock_toml.return_value = {
            'audio': {
                'initial_volume': 75
            }
        }
        
        # Configure mock
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = mock_amixer_output
        mock_run.return_value = mock_result

        player = RadioPlayer()
        assert player.get_volume() == 75

def test_get_volume_failure():
    """Test volume retrieval failure handling"""
    with patch('subprocess.run') as mock_run:
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_run.return_value = mock_result

        player = RadioPlayer()
        # Should return default volume
        assert player.get_volume() == player.volume

def test_volume_bounds():
    """Test volume bounds checking"""
    with patch('subprocess.run') as mock_run:
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        player = RadioPlayer()
        
        # Test upper bound
        player.set_volume(150)
        assert player.volume <= 100
        
        # Test lower bound
        player.set_volume(-50)
        assert player.volume >= 0

@pytest.mark.integration
def test_actual_volume_control():
    """Integration test for volume control"""
    player = RadioPlayer()
    
    # Test volume control sequence
    assert player.set_volume(50)
    current_volume = player.get_volume()
    assert abs(current_volume - 50) <= 5  # Allow small deviation
    
    assert player.set_volume(75)
    current_volume = player.get_volume()
    assert abs(current_volume - 75) <= 5  # Allow small deviation

@patch('src.player.radio_player.vlc')
@patch('subprocess.run')
def test_get_status(mock_subprocess, mock_vlc):
    """Test that get_status returns the correct status dictionary"""
    # Reset singleton state
    RadioPlayer._instance = None

    # Setup mock VLC instance
    mock_player = MagicMock()
    mock_media = MagicMock()
    mock_instance = MagicMock()
    mock_state = MagicMock()

    # Configure VLC mocks
    mock_vlc.Instance.return_value = mock_instance
    mock_instance.media_player_new.return_value = mock_player
    mock_instance.media_new.return_value = mock_media
    
    # Configure state mock
    mock_state.value = 3  # Playing state
    mock_player.get_state.return_value = mock_state
    
    # Configure player mock behavior
    mock_player.is_playing.side_effect = [False, True]
    mock_player.play.return_value = 0

    # Create player instance
    player = RadioPlayer()

    # Test initial status
    initial_status = player.get_status()
    assert initial_status == {
        'state': 'stopped',
        'current_station': None,
        'volume': 80
    }

    # Play the stream
    test_url = 'http://test.stream/url'
    player.play(test_url)

    # Test final status
    final_status = player.get_status()
    assert final_status == {
        'state': 'playing',
        'current_station': test_url,
        'volume': 80
    }

def test_alsa_device_configuration():
    """Test ALSA device configuration"""
    with patch('subprocess.run') as mock_run, \
         patch('src.player.radio_player.vlc') as mock_vlc, \
         patch('toml.load') as mock_toml:
        
        # Mock config
        mock_toml.return_value = {
            'audio': {
                'initial_volume': 75
            }
        }
        
        # Mock subprocess output for aplay -l
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "card 2: Headphones [bcm2835 Headphones]"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        # Create player instance
        player = RadioPlayer()
        
        # Verify VLC was configured with correct ALSA device
        expected_args = ' '.join([
            '--aout=alsa',
            '--alsa-audio-device=hw:2,0',
            '--verbose=2'
        ])
        mock_vlc.Instance.assert_called_with(expected_args)

def test_get_status():
    """Test getting player status"""
    with patch('src.player.radio_player.vlc') as mock_vlc, \
         patch('toml.load') as mock_toml:
        # Mock config
        mock_toml.return_value = {
            'audio': {
                'initial_volume': 75
            }
        }
        
        # Reset singleton
        RadioPlayer._instance = None
        
        # Create player
        player = RadioPlayer()
        
        # Get initial status
        status = player.get_status()
        
        # Verify status
        expected_status = {
            'state': 'stopped',
            'current_station': None,
            'volume': 75  # Default volume from mocked config
        }
        assert status == expected_status

def test_volume_initialization():
    """Test that volume is properly initialized"""
    with patch('src.player.radio_player.vlc') as mock_vlc, \
         patch('subprocess.run') as mock_run, \
         patch('toml.load') as mock_toml:
        # Reset singleton
        RadioPlayer._instance = None
        
        # Mock config
        mock_toml.return_value = {
            'audio': {
                'initial_volume': 75
            }
        }
        
        # Configure mock for volume control
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        # Create player
        player = RadioPlayer()
        
        # Verify initial volume
        assert player.current_status['volume'] == 75

def test_volume_control():
    """Test volume control functionality"""
    with patch('subprocess.run') as mock_run, \
         patch('toml.load') as mock_toml:
        # Configure mock for aplay -l
        aplay_result = Mock()
        aplay_result.returncode = 0
        aplay_result.stdout = "card 2: Headphones [bcm2835 Headphones]"
        
        # Configure mock for amixer
        amixer_result = Mock()
        amixer_result.returncode = 0
        amixer_result.stdout = "Simple mixer control 'PCM',0\n  Capabilities: pvolume\n  Playback channels: Front Left - Front Right\n  Limits: Playback -10239 - 400\n  Mono: Playback -1024 [75%] [-10.24dB]"
        amixer_result.stderr = ""
        
        # Set up mock to return different results based on the command
        def mock_run_side_effect(*args, **kwargs):
            if 'aplay' in args[0]:
                return aplay_result
            return amixer_result
            
        mock_run.side_effect = mock_run_side_effect
        
        # Mock config
        mock_toml.return_value = {
            'audio': {
                'initial_volume': 75
            }
        }
        
        # Reset singleton
        RadioPlayer._instance = None
        player = RadioPlayer()
        
        # Test setting volume
        assert player.set_volume(75) == True
        
        # Verify the exact command that was called
        mock_run.assert_called_with(
            ['amixer', 'sset', '-c', '2', 'PCM', '75%'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )