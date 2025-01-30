import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def get_network_service() -> Any:
    """Factory function to get the appropriate network service"""
    if os.getenv("MOCK_SERVICES") == "true":
        logger.info("Using mock network service")
        from src.mocks.network_mocks import MockNetworkManagerService

        return MockNetworkManagerService()

    # Use NetworkManager directly when not in mock mode
    logger.info("Using real NetworkManager service")
    from src.mocks.network_mocks import (  # Use mock for now as base class
        MockNetworkManagerService,
    )

    class NetworkManager(MockNetworkManagerService):
        """Real network manager that extends mock for consistent interface"""

        def __init__(self):
            super().__init__()
            self.logger = logging.getLogger(__name__)

    return NetworkManager()
