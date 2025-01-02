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

    # Import real service only when needed (not in dev/test)
    from src.hardware.network import NetworkManager

    return NetworkManager()
