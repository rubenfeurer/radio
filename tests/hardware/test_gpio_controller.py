import pytest
from unittest.mock import Mock, patch
from src.hardware.gpio_controller import GPIOController
from config.config import settings
import time

"""
Test suite for GPIO Controller.
Tests only implemented hardware interactions.

Currently implemented:
- Basic button press detection
- Basic rotary encoder movement
- Simple callbacks
"""

def test_gpio_init():
    """Test GPIO controller initialization"""
    with patch('pigpio.pi') as mock_pi:
        mock_instance = Mock()
        mock_instance.connected = True
        mock_pi.return_value = mock_instance

        controller = GPIOController()
        assert hasattr(controller, 'pi')
        assert controller.pi.connected

def test_button_callback():
    """Test basic button press callback"""
    mock_callback = Mock()
    with patch('pigpio.pi') as mock_pi:
        mock_instance = Mock()
        mock_instance.connected = True
        mock_pi.return_value = mock_instance

        controller = GPIOController(button_press_callback=mock_callback)
        controller._handle_button(settings.BUTTON_PIN_1, 1, 0)  # Simulate button release
        mock_callback.assert_called_once_with(1)

def test_volume_callback():
    """Test basic volume change callback"""
    mock_callback = Mock()
    with patch('pigpio.pi') as mock_pi:
        mock_instance = Mock()
        mock_instance.connected = True
        mock_pi.return_value = mock_instance

        controller = GPIOController(volume_change_callback=mock_callback)
        controller._handle_rotation(settings.ROTARY_CLK, 0, 0)
        mock_callback.assert_called_with(settings.ROTARY_VOLUME_STEP)

def test_rotation_direction():
    """Test rotary encoder direction detection"""
    mock_callback = Mock()
    with patch('pigpio.pi') as mock_pi:
        mock_instance = Mock()
        mock_instance.connected = True
        mock_pi.return_value = mock_instance

        controller = GPIOController(volume_change_callback=mock_callback)
        controller._handle_rotation(settings.ROTARY_CLK, 0, 0)
        mock_callback.assert_called_with(settings.ROTARY_VOLUME_STEP)

def test_long_press_detection():
    """Test long press detection"""
    mock_callback = Mock()
    with patch('pigpio.pi') as mock_pi:
        mock_instance = Mock()
        mock_instance.connected = True
        mock_pi.return_value = mock_instance

        controller = GPIOController(long_press_callback=mock_callback)
        gpio = settings.BUTTON_PIN_1

        # Simulate long press
        controller._handle_button(gpio, 0, 0)  # Button pressed
        time.sleep(settings.LONG_PRESS_DURATION + 0.1)  # Wait longer than long press duration
        controller._handle_button(gpio, 1, 0)  # Button released
        mock_callback.assert_called_once_with(1)

def test_double_press_detection():
    """Test double press detection"""
    mock_callback = Mock()
    with patch('pigpio.pi') as mock_pi:
        mock_instance = Mock()
        mock_instance.connected = True
        mock_pi.return_value = mock_instance

        controller = GPIOController(double_press_callback=mock_callback)
        gpio = settings.BUTTON_PIN_1

        # Simulate double press
        controller._handle_button(gpio, 1, 0)  # Button released
        time.sleep(settings.DOUBLE_PRESS_INTERVAL / 2)  # Wait less than double press interval
        controller._handle_button(gpio, 1, 0)  # Button released again
        mock_callback.assert_called_once_with(1) 