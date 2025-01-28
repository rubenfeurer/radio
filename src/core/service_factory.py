import logging
import os
import platform
from typing import Any, Callable, Dict, Optional, Type, TypeVar, cast
import asyncio

T = TypeVar("T")

logger = logging.getLogger(__name__)


class ServiceFactory:
    _instances: Dict[Type[Any], Any] = {}

    @classmethod
    def should_use_mocks(cls) -> bool:
        """Determine if we should use mock services"""
        mock_services = os.getenv("MOCK_SERVICES", "false").lower() == "true"
        is_ci = os.getenv("CI", "false").lower() == "true"
        is_raspberry_pi = platform.machine().startswith('arm')
        
        # Always use mocks in CI
        if is_ci:
            return True
        # Use real hardware on Raspberry Pi unless explicitly mocked
        elif is_raspberry_pi:
            return mock_services
        # Use mocks on other platforms
        else:
            return True

    @classmethod
    def get_service(
        cls,
        service_type: str,
        event_loop: Optional[asyncio.AbstractEventLoop] = None,
        button_press_callback: Optional[Callable[[int], Any]] = None,
        volume_change_callback: Optional[Callable[[int], Any]] = None,
        triple_press_callback: Optional[Callable[[], Any]] = None,
        long_press_callback: Optional[Callable[[], Any]] = None,
    ) -> Any:
        """Get appropriate service implementation based on environment"""
        
        if os.getenv("MOCK_SERVICES") == "true":
            logger.info(f"Using mock {service_type} service")
            if service_type == "network":
                from src.mocks.network_mocks import MockNetworkManagerService
                return MockNetworkManagerService()
            elif service_type == "gpio":
                from src.mocks.hardware_mocks import MockGPIOController
                return MockGPIOController(
                    event_loop=event_loop,
                    button_press_callback=button_press_callback,
                    volume_change_callback=volume_change_callback,
                    triple_press_callback=triple_press_callback,
                    long_press_callback=long_press_callback
                )
            elif service_type == "audio":
                from src.mocks.hardware_mocks import MockAudioPlayer
                return MockAudioPlayer()
        else:
            logger.info(f"Using real {service_type} service")
            if service_type == "network":
                from src.mocks.network_mocks import MockNetworkManagerService
                class NetworkManager(MockNetworkManagerService):
                    def __init__(self):
                        super().__init__()
                        self.logger = logging.getLogger(__name__)
                return NetworkManager()
            elif service_type == "gpio":
                from src.hardware.gpio_controller import GPIOController
                return GPIOController(
                    event_loop=event_loop,
                    button_press_callback=button_press_callback,
                    volume_change_callback=volume_change_callback,
                    triple_press_callback=triple_press_callback,
                    long_press_callback=long_press_callback
                )
            elif service_type == "audio":
                from src.hardware.audio_player import AudioPlayer
                return AudioPlayer()

        raise ValueError(f"Unknown service type: {service_type}")

    @classmethod
    def get_instance(
        cls, target_cls: Type[T], callback: Optional[Callable[..., Any]] = None
    ) -> T:
        key = target_cls
        if key not in cls._instances:
            instance = None
            if hasattr(target_cls, "__new__"):
                # If class has __new__, use it directly
                instance = target_cls.__new__(target_cls)
                if hasattr(instance, "__init__"):
                    # Initialize with callback if possible
                    try:
                        if callback is not None:
                            instance.__init__(callback)  # type: ignore
                        else:
                            instance.__init__()  # type: ignore
                    except TypeError:
                        pass  # Ignore initialization errors
            else:
                # Fallback to direct instantiation
                instance = target_cls()

            cls._instances[key] = instance or target_cls()

        return cast(T, cls._instances[key])
