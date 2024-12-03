import pytest
from unittest.mock import Mock, patch
from src.hardware.gpio_controller import GPIOController
from config.config import settings, Settings
import os

@pytest.fixture
def gpio_controller():
    # Mock pigpio
    with patch('pigpio.pi') as mock_pi:
        # Setup mock pi instance
        mock_instance = Mock()
        mock_instance.connected = True
        mock_pi.return_value = mock_instance
        
        # Create controller
        controller = GPIOController()
        yield controller
        
        # Cleanup
        if hasattr(controller, 'pi'):
            controller.cleanup()

def test_gpio_init(gpio_controller):
    assert hasattr(gpio_controller, 'pi')
    assert gpio_controller.pi.connected

@pytest.mark.asyncio
async def test_volume_callback():
    mock_callback = Mock()
    with patch('pigpio.pi') as mock_pi:
        # Setup mock pi instance
        mock_instance = Mock()
        mock_instance.connected = True
        mock_instance.read.return_value = 1  # Mock DT state
        mock_pi.return_value = mock_instance
        
        controller = GPIOController(volume_change_callback=mock_callback)
        # Simulate rotation with required arguments (gpio, level, tick)
        controller._handle_rotation(settings.ROTARY_CLK, 0, 0)
        
        mock_callback.assert_called_once_with(controller.volume_step)

@pytest.mark.asyncio
async def test_button_callback():
    mock_callback = Mock()
    with patch('pigpio.pi') as mock_pi:
        # Setup mock pi instance
        mock_instance = Mock()
        mock_instance.connected = True
        mock_pi.return_value = mock_instance
        
        controller = GPIOController(button_press_callback=mock_callback)
        # Simulate button press with required arguments (gpio, level, tick)
        controller._handle_button(settings.BUTTON_PIN_1, 0, 0)
        
        mock_callback.assert_called_once_with(1)

@pytest.mark.asyncio
async def test_rotation_direction():
    mock_callback = Mock()
    with patch('pigpio.pi') as mock_pi:
        # Setup mock pi instance
        mock_instance = Mock()
        mock_instance.connected = True
        mock_pi.return_value = mock_instance
        
        # Test counter-clockwise rotation
        test_settings = Settings(ROTARY_CLOCKWISE_INCREASES=False)
        with patch('src.hardware.gpio_controller.settings', test_settings):
            controller = GPIOController(volume_change_callback=mock_callback)
            
            # Mock DT state for counter-clockwise
            mock_instance.read.return_value = 0
            controller._handle_rotation(settings.ROTARY_CLK, 0, 0)
            mock_callback.assert_called_with(controller.volume_step)
            
            # Reset mock and test clockwise
            mock_callback.reset_mock()
            mock_instance.read.return_value = 1
            controller._handle_rotation(settings.ROTARY_CLK, 0, 0)
            mock_callback.assert_called_with(-controller.volume_step)

# ... (rest of the test cases remain the same) 