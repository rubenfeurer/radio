import pytest
from unittest.mock import Mock, patch
from src.hardware.rotary_handler import RotaryHandler

@pytest.fixture(autouse=True)
def mock_gpio():
    with patch('src.hardware.rotary_handler.GPIO') as mock:
        # Setup GPIO mock
        mock.BCM = 11
        mock.IN = 1
        mock.FALLING = 2
        mock.RISING = 3
        mock.BOTH = 4
        mock.PUD_UP = 22
        mock.setmode = Mock()
        mock.setup = Mock()
        mock.add_event_detect = Mock()
        
        # Create a stateful input mock that returns values in sequence
        mock.input = Mock()
        
        yield mock

@pytest.fixture
def mock_player():
    player = Mock()
    player.get_volume.return_value = 50
    return player

@pytest.fixture
def mock_system():
    with patch('os.system') as mock:
        yield mock

@pytest.fixture
def mock_config(tmp_path):
    config = {
        "rotary": {
            "clk_pin": 11,
            "dt_pin": 9,
            "sw_pin": 10,
            "settings": {
                "volume_step": 5,
                "double_click_timeout": 500,
                "debounce_time": 50
            }
        }
    }
    config_path = tmp_path / "config.toml"
    
    with open(config_path, "w") as f:
        f.write("""
[rotary]
clk_pin = 11
dt_pin = 9
sw_pin = 10

[rotary.settings]
volume_step = 5
double_click_timeout = 500
debounce_time = 50
""")
    
    return str(config_path)

@pytest.fixture
def rotary_handler(mock_gpio, mock_player, mock_config):
    handler = RotaryHandler(config_file=mock_config)
    handler.player = mock_player
    # Initialize last_clk_state
    mock_gpio.input.return_value = 0
    handler.last_clk_state = 0
    return handler

@pytest.fixture
def mock_time():
    with patch('src.hardware.rotary_handler.time') as mock:
        mock.return_value = 0
        yield mock

def test_volume_up(rotary_handler, mock_gpio):
    """Test volume increase when rotating clockwise"""
    current_volume = rotary_handler.player.get_volume()
    
    # Setup GPIO states for clockwise rotation
    mock_gpio.input.side_effect = [1, 1]  # CLK=1, DT=1 for clockwise
    
    rotary_handler.clk_callback(11)
    rotary_handler.player.set_volume.assert_called_with(current_volume + 5)

def test_volume_down(rotary_handler, mock_gpio):
    """Test volume decrease when rotating counter-clockwise"""
    current_volume = rotary_handler.player.get_volume()
    
    # Setup GPIO states for counter-clockwise rotation
    mock_gpio.input.side_effect = [0, 0]  # CLK=0, DT=0 for counter-clockwise
    
    rotary_handler.dt_callback(9)
    rotary_handler.player.set_volume.assert_called_with(current_volume - 5)

def test_volume_limits(rotary_handler, mock_gpio):
    """Test volume stays within 0-100 range"""
    # Test upper limit
    rotary_handler.player.get_volume.return_value = 98
    mock_gpio.input.side_effect = [1, 1]  # CLK=1, DT=1 for clockwise
    rotary_handler.clk_callback(11)
    rotary_handler.player.set_volume.assert_called_with(100)
    
    # Reset mocks
    rotary_handler.player.set_volume.reset_mock()
    mock_gpio.input.reset_mock()
    
    # Test lower limit
    rotary_handler.player.get_volume.return_value = 2
    mock_gpio.input.side_effect = [0, 0]  # CLK=0, DT=0 for counter-clockwise
    rotary_handler.dt_callback(9)
    rotary_handler.player.set_volume.assert_called_with(0)

def test_double_click_reboot(rotary_handler, mock_system, mock_time):
    """Test double click triggers reboot"""
    # Simulate first click
    mock_time.return_value = 0
    rotary_handler.sw_callback(10)
    
    # Simulate second click within timeout
    mock_time.return_value = 0.3  # 300ms later
    rotary_handler.sw_callback(10)
    mock_system.assert_called_with('sudo reboot')

def test_single_click_no_reboot(rotary_handler, mock_system, mock_time):
    """Test single click doesn't trigger reboot"""
    # Simulate first click at t=0
    mock_time.return_value = 0.0
    rotary_handler.sw_callback(10)
    
    # Simulate time passing beyond double-click timeout
    mock_time.return_value = 1.0  # 1 second later
    rotary_handler.sw_callback(10)  # Second click after timeout
    
    mock_system.assert_not_called() 