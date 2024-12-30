import os
from typing import Any
from src.mocks import MockNetworkManager, MockGPIOController, MockAudioPlayer

class ServiceFactory:
    @staticmethod
    def get_service(service_type: str) -> Any:
        use_mocks = os.getenv('MOCK_SERVICES', 'false').lower() == 'true'
        
        if use_mocks:
            services = {
                'network': MockNetworkManager,
                'gpio': MockGPIOController,
                'audio': MockAudioPlayer
            }
            return services.get(service_type)()
        
        # Return real implementations
        if service_type == 'network':
            from src.hardware.network import NetworkManager
            return NetworkManager()
        elif service_type == 'gpio':
            from src.hardware.gpio import GPIOController
            return GPIOController()
        elif service_type == 'audio':
            from src.hardware.audio import AudioPlayer
            return AudioPlayer() 