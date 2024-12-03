import pytest
from unittest.mock import Mock, patch
from src.hardware.gpio_controller import GPIOController
from src.core.config import settings, Settings
import os

@pytest.fixture
def gpio_controller():
    # Store original environment state
    original_env = os.environ.get('PYTEST_CURRENT_TEST')
    
    # Set test environment
    os.environ['PYTEST_CURRENT_TEST'] = 'test_mode'
    
    # Create controller
    with patch('RPi.GPIO'):
        controller = GPIOController()
        yield controller
    
    # Restore original environment state
    if original_env:
        os.environ['PYTEST_CURRENT_TEST'] = original_env
    elif 'PYTEST_CURRENT_TEST' in os.environ:
        del os.environ['PYTEST_CURRENT_TEST']

def test_gpio_init(gpio_controller):
    assert gpio_controller.is_initialized == True

@pytest.mark.asyncio
async def test_volume_callback():
    mock_callback = Mock()
    with patch('RPi.GPIO.input') as mock_input:
        # Setup GPIO mock
        mock_input.side_effect = [0, 1]  # CLK=0, DT=1 for clockwise
        
        # Ensure the default setting is used
        test_settings = Settings(ROTARY_CLOCKWISE_INCREASES=True)
        with patch('src.hardware.gpio_controller.settings', test_settings):
            controller = GPIOController(volume_change_callback=mock_callback)
            controller._handle_rotation(0)  # Simulate rotation
            mock_callback.assert_called_once_with(controller.volume_step)

@pytest.mark.asyncio
async def test_button_callback():
    mock_callback = Mock()
    with patch('RPi.GPIO') as mock_gpio:
        controller = GPIOController(button_press_callback=mock_callback)
        controller._handle_button(settings.BUTTON_PIN_1)  # Simulate button 1 press
        mock_callback.assert_called_once_with(1)

@pytest.mark.asyncio
async def test_rotation_direction():
    mock_callback = Mock()
    with patch('RPi.GPIO.input') as mock_input:
        # Create a new settings instance for testing
        test_settings = Settings(ROTARY_CLOCKWISE_INCREASES=False)
        
        # Patch the settings in the gpio_controller module
        with patch('src.hardware.gpio_controller.settings', test_settings):
            controller = GPIOController(volume_change_callback=mock_callback)
            
            # Test clockwise rotation (CLK=0, DT=1)
            mock_input.side_effect = [0, 1]
            controller._handle_rotation(0)
            mock_callback.assert_called_with(-controller.volume_step)
            
            # Reset mock
            mock_callback.reset_mock()
            # Test counter-clockwise rotation (CLK=0, DT=0)
            mock_input.side_effect = [0, 0]
            controller._handle_rotation(0)
            mock_callback.assert_called_with(controller.volume_step)

# ... (rest of the test cases remain the same) 