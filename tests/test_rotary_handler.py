from unittest.mock import Mock, patch, mock_open
import pytest
from RPi import GPIO
from src.hardware.rotary_handler import RotaryHandler
from src.player.radio_player import RadioPlayer
import toml
from unittest.mock import MagicMock
from time import time
import os
import logging
from unittest.mock import call
import sys

class MockGPIO:
    """Mock GPIO class that replaces RPi.GPIO"""
    BCM = 11
    IN = 1
    PUD_UP = 22
    FALLING = 31
    BOTH = 33
    
    def __init__(self):
        self._setup_pins = set()
        self._pin_values = {}
        self._event_callbacks = {}
        
        # Create Mock objects for methods
        self.setmode = Mock()
        self.cleanup = Mock()
        self.add_event_detect = Mock()
        
        # Use real implementations for these methods
        self.setup = self._setup
        self.input = self._input
        
    def _setup(self, channel, direction, pull_up_down=None):
        """Real implementation of setup"""
        self._setup_pins.add(channel)
        self._pin_values[channel] = 0
        
    def _input(self, channel):
        """Real implementation of input"""
        if channel not in self._setup_pins:
            raise RuntimeError('You must setup() the GPIO channel first')
        return self._pin_values.get(channel, 0)
            
    # Helper methods for testing
    def trigger_input(self, channel, value):
        self._pin_values[channel] = value
        
    def trigger_event(self, channel):
        if channel in self._event_callbacks:
            self._event_callbacks[channel](channel)

@pytest.fixture(autouse=True)
def mock_gpio_setup():
    """Mock both GPIO and lgpio modules"""
    # Create mock lgpio module
    mock_lgpio = Mock()
    mock_lgpio._u2i = Mock(return_value=0)
    mock_lgpio.gpio_claim_input = Mock(return_value=0)
    mock_lgpio.gpio_claim_alert = Mock(return_value=0)
    mock_lgpio.gpiochip_open = Mock(return_value=0)
    mock_lgpio._lgpio = Mock()
    mock_lgpio._lgpio._gpio_claim_input = Mock(return_value=0)
    mock_lgpio._lgpio._gpio_claim_alert = Mock(return_value=0)
    
    # Create mock GPIO module
    mock_gpio = Mock()
    mock_gpio.BCM = 11
    mock_gpio.IN = 1
    mock_gpio.PUD_UP = 22
    mock_gpio.FALLING = 31
    mock_gpio.BOTH = 33
    mock_gpio.setmode = Mock()
    mock_gpio.setup = Mock()
    mock_gpio.input = Mock(return_value=0)
    mock_gpio.add_event_detect = Mock()
    mock_gpio.cleanup = Mock()
    mock_gpio.lgpio = mock_lgpio
    
    # Create patch context
    with patch.dict('sys.modules', {
        'lgpio': mock_lgpio,
        'RPi.GPIO': mock_gpio
    }), patch('src.hardware.rotary_handler.GPIO', mock_gpio):
        yield mock_gpio

@pytest.fixture
def mock_config():
    """Mock configuration data"""
    return {
        'gpio': {
            'rotary': {
                'clk': 11,
                'dt': 9,
                'sw': 10
            }
        },
        'rotary': {
            'settings': {
                'clockwise_increases': True,
                'debounce_time': 50,
                'double_click_timeout': 500,
                'volume_step': 5
            }
        }
    }

@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the RotaryHandler singleton before each test"""
    RotaryHandler._instance = None
    yield
    if RotaryHandler._instance is not None:
        RotaryHandler._instance.cleanup()
    RotaryHandler._instance = None

@pytest.fixture
def rotary_handler(mock_gpio_setup, mock_config):
    """Create a RotaryHandler instance for testing"""
    mock_player = Mock(spec=['get_volume', 'set_volume'])
    mock_player.get_volume.return_value = 50
    
    with patch('tomli.load', return_value=mock_config), \
         patch('builtins.open', mock_open()):
        
        handler = RotaryHandler(radio_player=mock_player)
        yield handler
        
        if handler:
            handler.cleanup()

def test_volume_up(rotary_handler, mock_gpio_setup):
    """Test volume increase when rotating clockwise"""
    # Configure logging for debugging
    logging.basicConfig(level=logging.DEBUG)
    
    initial_volume = 50
    rotary_handler.radio_player.get_volume.return_value = initial_volume
    
    # Set initial state
    rotary_handler.last_clk = 1
    rotary_handler.last_dt = 1
    
    # Setup GPIO states for clockwise rotation
    def mock_input(pin):
        if pin == rotary_handler.clk_pin:
            return 0  # CLK goes low first
        elif pin == rotary_handler.dt_pin:
            return 1  # DT stays high
        return 1
    
    # Patch GPIO at the module level
    with patch('src.hardware.rotary_handler.GPIO') as patched_gpio:
        # Configure the mock
        patched_gpio.input = Mock(side_effect=mock_input)
        
        # Verify initial state
        assert rotary_handler.last_clk == 1
        assert rotary_handler.last_dt == 1
        assert patched_gpio.input(rotary_handler.clk_pin) == 0
        assert patched_gpio.input(rotary_handler.dt_pin) == 1
        
        # Trigger rotation
        rotary_handler._clk_callback(None)
        
        # Verify volume was increased
        rotary_handler.radio_player.set_volume.assert_called_once_with(initial_volume + 5)

def test_volume_down(rotary_handler, mock_gpio_setup):
    """Test volume decrease when rotating counter-clockwise"""
    # Configure logging for debugging
    logging.basicConfig(level=logging.DEBUG)
    
    initial_volume = 50
    rotary_handler.radio_player.get_volume.return_value = initial_volume
    
    # Set initial state
    rotary_handler.last_clk = 1
    rotary_handler.last_dt = 1
    
    # Setup GPIO states for counter-clockwise rotation
    def mock_input(pin):
        if pin == rotary_handler.clk_pin:
            return 0  # CLK goes low
        elif pin == rotary_handler.dt_pin:
            return 0  # DT also goes low for counter-clockwise
        return 1
    
    # Patch GPIO at the module level
    with patch('src.hardware.rotary_handler.GPIO') as patched_gpio:
        # Configure the mock
        patched_gpio.input = Mock(side_effect=mock_input)
        
        # Verify initial state
        assert rotary_handler.last_clk == 1
        assert rotary_handler.last_dt == 1
        assert patched_gpio.input(rotary_handler.clk_pin) == 0
        assert patched_gpio.input(rotary_handler.dt_pin) == 0
        
        # Trigger rotation
        rotary_handler._clk_callback(None)
        
        # Verify volume was decreased
        rotary_handler.radio_player.set_volume.assert_called_once_with(initial_volume - 5)

def test_volume_limits(rotary_handler, mock_gpio_setup):
    """Test volume limits (0-100)"""
    # Configure logging for debugging
    logging.basicConfig(level=logging.DEBUG)
    
    # Test upper limit
    rotary_handler.radio_player.get_volume.return_value = 98
    rotary_handler.last_clk = 1
    rotary_handler.last_dt = 1
    
    # Setup GPIO states for clockwise rotation (volume up)
    def mock_input_up(pin):
        if pin == rotary_handler.clk_pin:
            return 0  # CLK goes low
        elif pin == rotary_handler.dt_pin:
            return 1  # DT stays high
        return 1
    
    # Patch GPIO at the module level
    with patch('src.hardware.rotary_handler.GPIO') as patched_gpio:
        # Configure the mock for volume up
        patched_gpio.input = Mock(side_effect=mock_input_up)
        
        # Trigger rotation
        rotary_handler._clk_callback(None)
        
        # Verify volume was capped at 100
        rotary_handler.radio_player.set_volume.assert_called_once_with(100)
        
        # Reset mock
        rotary_handler.radio_player.set_volume.reset_mock()
    
    # Test lower limit
    rotary_handler.radio_player.get_volume.return_value = 2
    rotary_handler.last_clk = 1
    rotary_handler.last_dt = 1
    
    # Setup GPIO states for counter-clockwise rotation (volume down)
    def mock_input_down(pin):
        if pin == rotary_handler.clk_pin:
            return 0  # CLK goes low
        elif pin == rotary_handler.dt_pin:
            return 0  # DT also goes low
        return 1
    
    # Patch GPIO again for volume down
    with patch('src.hardware.rotary_handler.GPIO') as patched_gpio:
        # Configure the mock for volume down
        patched_gpio.input = Mock(side_effect=mock_input_down)
        
        # Trigger rotation
        rotary_handler._clk_callback(None)
        
        # Verify volume was capped at 0
        rotary_handler.radio_player.set_volume.assert_called_once_with(0)

def test_single_click_no_reboot(rotary_handler, mock_gpio_setup):
    """Test that a single click doesn't trigger reboot"""
    base_time = 1000.0
    
    with patch('os.system') as mock_system, \
         patch('time.time', return_value=base_time):
        rotary_handler._button_callback(None)
        mock_system.assert_not_called()

def test_double_click_reboot(rotary_handler, mock_gpio_setup):
    """Test that a double click triggers system reboot"""
    base_time = 1000.0
    
    with patch('os.system') as mock_system:
        # First click
        with patch('time.time', return_value=base_time):
            rotary_handler._button_callback(None)
            mock_system.assert_not_called()
        
        # Second click within timeout
        with patch('time.time', return_value=base_time + 0.3):
            rotary_handler._button_callback(None)
            mock_system.assert_called_once_with('sudo reboot')

def test_rotary_volume_control(rotary_handler, mock_gpio_setup):
    """Test rotary encoder volume control"""
    # Configure logging for debugging
    logging.basicConfig(level=logging.DEBUG)
    
    initial_volume = 50
    rotary_handler.radio_player.get_volume.return_value = initial_volume
    
    # Set initial state
    rotary_handler.last_clk = 1
    rotary_handler.last_dt = 1
    
    # Test clockwise rotation (volume up)
    with patch('src.hardware.rotary_handler.GPIO') as patched_gpio:
        def mock_input_up(pin):
            if pin == rotary_handler.clk_pin:
                return 0  # CLK goes low
            elif pin == rotary_handler.dt_pin:
                return 1  # DT stays high
            return 1
            
        patched_gpio.input = Mock(side_effect=mock_input_up)
        
        # Trigger rotation
        rotary_handler._clk_callback(None)
        
        # Verify volume was increased
        rotary_handler.radio_player.set_volume.assert_called_once_with(initial_volume + 5)
        rotary_handler.radio_player.set_volume.reset_mock()
    
    # Reset state for counter-clockwise test
    rotary_handler.last_clk = 1
    rotary_handler.last_dt = 1
    
    # Test counter-clockwise rotation (volume down)
    with patch('src.hardware.rotary_handler.GPIO') as patched_gpio:
        def mock_input_down(pin):
            if pin == rotary_handler.clk_pin:
                return 0  # CLK goes low
            elif pin == rotary_handler.dt_pin:
                return 0  # DT also goes low
            return 1
            
        patched_gpio.input = Mock(side_effect=mock_input_down)
        
        # Trigger rotation
        rotary_handler._clk_callback(None)
        
        # Verify volume was decreased
        rotary_handler.radio_player.set_volume.assert_called_once_with(initial_volume - 5)

def test_smooth_rotation(rotary_handler, mock_gpio_setup):
    """Test smooth rotation handling"""
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.DEBUG)
    
    initial_volume = 50
    current_volume = initial_volume
    rotary_handler.radio_player.get_volume.return_value = current_volume
    
    # Set initial state
    rotary_handler.last_clk = 1
    rotary_handler.last_dt = 1
    
    # Test multiple clockwise rotations
    with patch('src.hardware.rotary_handler.GPIO') as patched_gpio:
        def mock_input(pin):
            nonlocal current_volume
            # Always return the initial state for other pins
            if pin != rotary_handler.clk_pin and pin != rotary_handler.dt_pin:
                return 1
                
            # First rotation: CLK goes low, DT stays high
            if rotary_handler.last_clk == 1:
                if pin == rotary_handler.clk_pin:
                    return 0  # Trigger volume up
                return 1  # DT stays high
            
            # After volume change, return to initial state
            return 1
            
        patched_gpio.input = Mock(side_effect=mock_input)
        
        # First rotation
        rotary_handler._clk_callback(None)
        current_volume += 5
        rotary_handler.radio_player.get_volume.return_value = current_volume
        
        # Reset for second rotation
        rotary_handler.last_clk = 1
        rotary_handler.last_dt = 1
        
        # Second rotation
        rotary_handler._clk_callback(None)
        
        # Verify volume changes
        expected_calls = [
            call(initial_volume + 5),  # First rotation
            call(initial_volume + 10)   # Second rotation
        ]
        assert rotary_handler.radio_player.set_volume.call_args_list == expected_calls

def test_gpio_setup(mock_gpio_setup):
    """Test GPIO pins are properly set up during initialization"""
    # Create mock player
    mock_player = Mock(spec=['get_volume', 'set_volume'])
    mock_config = {
        'gpio': {
            'rotary': {
                'clk': 11,
                'dt': 9,
                'sw': 10
            }
        },
        'rotary': {
            'settings': {
                'clockwise_increases': True,
                'debounce_time': 50,
                'double_click_timeout': 500,
                'volume_step': 5
            }
        }
    }

    # Patch at the module level where it's imported
    with patch('src.hardware.rotary_handler.GPIO', mock_gpio_setup), \
         patch('tomli.load', return_value=mock_config), \
         patch('builtins.open', mock_open()):
        
        # Create handler
        handler = RotaryHandler(radio_player=mock_player)
        
        # Verify GPIO mode was set
        mock_gpio_setup.setmode.assert_called_once_with(mock_gpio_setup.BCM)
        
        # Verify pin setup calls
        setup_calls = mock_gpio_setup.setup.call_args_list
        expected_pins = [mock_config['gpio']['rotary']['clk'],
                        mock_config['gpio']['rotary']['dt'],
                        mock_config['gpio']['rotary']['sw']]
        
        for pin in expected_pins:
            assert any(call[0][0] == pin for call in setup_calls)
    
def test_config_file_path(mock_gpio_setup):
    """Test that config file is loaded from the correct path"""
    mock_player = Mock(spec=['get_volume', 'set_volume'])
    mock_config = {
        'gpio': {
            'rotary': {
                'clk': 11,
                'dt': 9,
                'sw': 10
            }
        },
        'rotary': {
            'settings': {
                'clockwise_increases': True,
                'debounce_time': 50,
                'double_click_timeout': 500,
                'volume_step': 5
            }
        }
    }

    # Mock the os.path functions to return consistent values
    with patch('src.hardware.rotary_handler.GPIO', mock_gpio_setup), \
         patch('tomli.load', return_value=mock_config) as mock_load, \
         patch('builtins.open', mock_open()) as mock_file, \
         patch('os.path.dirname') as mock_dirname:
        
        # Set up the dirname mock to return expected values
        mock_dirname.side_effect = [
            '/home/radio/internetRadio/src/hardware',
            '/home/radio/internetRadio/src',
            '/home/radio/internetRadio'
        ]
        
        handler = RotaryHandler(radio_player=mock_player)
        
        # Verify the correct path was used
        expected_path = '/home/radio/internetRadio/config/config.toml'
        mock_file.assert_called_once_with(expected_path, 'rb')
    