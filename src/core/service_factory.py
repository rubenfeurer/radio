import os
from typing import Any, Callable, Dict, Optional, Type, TypeVar, cast

T = TypeVar("T")


class ServiceFactory:
    _instances: Dict[Type[Any], Any] = {}

    @classmethod
    def get_service(cls, service_type: str) -> Any:
        use_mocks = os.getenv("MOCK_SERVICES", "false").lower() == "true"

        if use_mocks:
            from src.mocks import (
                MockAudioPlayer,
                MockGPIOController,
                MockNetworkManager,
            )

            services = {
                "network": MockNetworkManager,
                "gpio": MockGPIOController,
                "audio": MockAudioPlayer,
            }
            service_class = services.get(service_type)
            if service_class is None:
                raise ValueError(f"Unknown service type: {service_type}")
            return service_class()

        # Return real implementations
        if service_type == "network":
            from src.hardware.network import NetworkManager

            return NetworkManager()
        if service_type == "gpio":
            from src.hardware.gpio import GPIOController

            return GPIOController()
        if service_type == "audio":
            from src.hardware.audio import AudioPlayer

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
