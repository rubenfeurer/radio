import pytest
from unittest.mock import Mock, patch
from src.hardware.gpio_controller import GPIOController
from config.config import settings
import time
import asyncio
from unittest.mock import AsyncMock

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
    with patch("pigpio.pi") as mock_pi:
        mock_instance = Mock()
        mock_instance.connected = True
        mock_pi.return_value = mock_instance

        controller = GPIOController()
        assert hasattr(controller, "pi")
        assert controller.pi.connected


def test_button_callback():
    """Test basic button press callback"""
    mock_callback = Mock()
    with patch("pigpio.pi") as mock_pi:
        mock_instance = Mock()
        mock_instance.connected = True
        mock_pi.return_value = mock_instance

        # Create event loop for testing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        controller = GPIOController(
            button_press_callback=mock_callback, event_loop=loop
        )
        # Simulate full button press cycle
        controller._handle_button(settings.BUTTON_PIN_1, 0, 0)  # Press
        controller._handle_button(settings.BUTTON_PIN_1, 1, 0)  # Release

        # Run pending callbacks
        loop.run_until_complete(asyncio.sleep(0))
        mock_callback.assert_called_once_with(1)


def test_volume_callback():
    """Test basic volume change callback"""
    mock_callback = Mock()
    with patch("pigpio.pi") as mock_pi:
        mock_instance = Mock()
        mock_instance.connected = True
        # Mock the DT pin read to simulate rotation direction
        mock_instance.read.return_value = 0  # Simulate clockwise rotation
        mock_pi.return_value = mock_instance

        # Create event loop for testing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        controller = GPIOController(
            volume_change_callback=mock_callback, event_loop=loop
        )
        # Simulate rotation with proper DT pin state
        controller._handle_rotation(settings.ROTARY_CLK, 1, 0)

        # Run pending callbacks
        loop.run_until_complete(asyncio.sleep(0))

        # Check if callback was called with correct volume change
        expected_change = (
            settings.ROTARY_VOLUME_STEP
            if settings.ROTARY_CLOCKWISE_INCREASES
            else -settings.ROTARY_VOLUME_STEP
        )
        mock_callback.assert_called_with(expected_change)


def test_rotation_direction():
    """Test rotary encoder direction detection"""
    mock_callback = Mock()
    with patch("pigpio.pi") as mock_pi:
        mock_instance = Mock()
        mock_instance.connected = True
        # Mock the DT pin read for both directions
        mock_instance.read.return_value = 0  # Simulate clockwise rotation
        mock_pi.return_value = mock_instance

        # Create event loop for testing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        controller = GPIOController(
            volume_change_callback=mock_callback, event_loop=loop
        )

        # Test clockwise rotation
        controller._handle_rotation(settings.ROTARY_CLK, 1, 0)
        loop.run_until_complete(asyncio.sleep(0))

        expected_change = (
            settings.ROTARY_VOLUME_STEP
            if settings.ROTARY_CLOCKWISE_INCREASES
            else -settings.ROTARY_VOLUME_STEP
        )
        mock_callback.assert_called_with(expected_change)


@pytest.mark.asyncio
async def test_long_press_detection():
    """Test long press detection"""
    mock_callback = AsyncMock()  # Use AsyncMock instead of Mock
    with patch("pigpio.pi") as mock_pi:
        mock_instance = Mock()
        mock_instance.connected = True
        mock_pi.return_value = mock_instance

        # Create event loop for testing
        loop = asyncio.get_event_loop()

        controller = GPIOController(long_press_callback=mock_callback, event_loop=loop)
        gpio = settings.ROTARY_SW  # Use rotary switch for long press

        # Simulate long press
        controller._handle_button(gpio, 0, 0)  # Press down
        await asyncio.sleep(
            settings.LONG_PRESS_DURATION + 0.1
        )  # Wait longer than threshold
        controller._handle_button(gpio, 1, 0)  # Release

        # Wait for callbacks to complete
        await asyncio.sleep(0.1)

        # Check if long press callback was called
        assert mock_callback.call_count == 1
        mock_callback.assert_called_once_with(gpio)


@pytest.mark.asyncio
async def test_triple_press_detection():
    """Test triple press detection"""
    mock_callback = AsyncMock()  # Use AsyncMock instead of Mock
    with patch("pigpio.pi") as mock_pi:
        mock_instance = Mock()
        mock_instance.connected = True
        mock_pi.return_value = mock_instance

        # Create event loop for testing
        loop = asyncio.get_event_loop()

        controller = GPIOController(
            triple_press_callback=mock_callback, event_loop=loop
        )
        gpio = settings.ROTARY_SW  # Use rotary switch for triple press

        # Simulate triple press with proper timing
        for _ in range(3):
            controller._handle_button(gpio, 0, 0)  # Press
            await asyncio.sleep(0.05)  # Short press duration
            controller._handle_button(gpio, 1, 0)  # Release
            await asyncio.sleep(0.1)  # Short interval between presses

        # Wait for callbacks to complete
        await asyncio.sleep(0.2)

        # Check if triple press callback was called
        assert mock_callback.call_count == 1
        mock_callback.assert_called_once_with(gpio)
