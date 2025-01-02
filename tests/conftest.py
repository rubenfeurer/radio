import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from src.core.wifi_manager import WiFiManager

# Add project root to Python path BEFORE imports
project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Create module level mocks
mock_mpv_instance: Optional[MagicMock] = None
mock_pi_instance: Optional[MagicMock] = None


@pytest.fixture(autouse=True)
def mock_hardware(monkeypatch) -> Optional[Dict[str, MagicMock]]:
    """Mock hardware components for testing."""
    if os.getenv("GITHUB_ACTIONS") or os.getenv("MOCK_HARDWARE") == "true":
        global mock_mpv_instance, mock_pi_instance

        # Create fresh MPV mock
        mock_mpv_instance = MagicMock()
        mock_mpv_instance.play = MagicMock()
        mock_mpv_instance.stop = MagicMock()
        type(mock_mpv_instance).volume = PropertyMock(return_value=50)

        # Create MPV class mock
        mock_mpv = MagicMock()
        mock_mpv.MPV.return_value = mock_mpv_instance

        # Create fresh pigpio mock
        mock_pi_instance = MagicMock()
        mock_pi_instance.connected = True
        mock_pi_instance.read = MagicMock(return_value=1)
        mock_pi_instance.callback = MagicMock()
        mock_pi_instance.set_mode = MagicMock()
        mock_pi_instance.set_pull_up_down = MagicMock()

        # Add required constants
        mock_pi_instance.INPUT = 0
        mock_pi_instance.OUTPUT = 1
        mock_pi_instance.PUD_UP = 2
        mock_pi_instance.FALLING_EDGE = 3
        mock_pi_instance.RISING_EDGE = 4

        # Create pigpio module mock
        mock_pigpio = MagicMock()
        mock_pigpio.pi.return_value = mock_pi_instance

        # Patch both modules
        monkeypatch.setattr("mpv.MPV", mock_mpv.MPV)
        monkeypatch.setattr("pigpio.pi", mock_pigpio.pi)

        return {"mpv": mock_mpv_instance, "pi": mock_pi_instance}
    return None


# Add cleanup
@pytest.fixture(autouse=True)
def cleanup() -> None:
    """Clean up mock instances after each test."""
    yield
    global mock_mpv_instance, mock_pi_instance
    if mock_mpv_instance:
        mock_mpv_instance.reset_mock()
    if mock_pi_instance:
        mock_pi_instance.reset_mock()


@pytest.fixture
def mock_websocket() -> MagicMock:
    """Mock WebSocket for testing."""
    mock_ws = MagicMock()
    mock_ws.send = MagicMock()
    mock_ws.receive_json = MagicMock(return_value={"type": "status_request"})
    return mock_ws


@pytest.fixture
def mock_radio_manager() -> MagicMock:
    """Mock RadioManager for testing."""
    mock_manager = MagicMock()
    mock_manager.get_status.return_value = {
        "volume": 50,
        "current_station": None,
        "is_playing": False,
    }
    return mock_manager


@pytest.fixture
def mock_wifi_process() -> MagicMock:
    """Create a basic WiFi process mock with success status."""
    process = MagicMock()
    process.returncode = 0
    process.stderr = ""
    process.stdout = "active"  # Default response
    return process


@pytest.fixture
def mock_networkmanager(mock_wifi_process) -> MagicMock:
    """Mock NetworkManager for WiFi testing."""

    def command_response(*args: Any, **kwargs: Any) -> MagicMock:
        command = args[0]
        process = MagicMock()
        process.returncode = 0
        process.stderr = ""

        if "is-active" in command:
            process.stdout = "active"
        elif "wifi" in command and "rescan" in command:
            process.stdout = ""
        elif "wifi" in command and "list" in command:
            if "ifname" in command:  # Current connection check
                process.stdout = "MyNetwork:90:WPA2:*:yes"
            else:  # Network scan
                process.stdout = (
                    "MyNetwork:90:WPA2:*:yes\n"
                    "OtherNetwork:85:WPA2::no\n"
                    "ThirdNetwork:70:WPA1::no"
                )
        elif "connectivity" in command:
            process.stdout = "full"
        else:
            process.stdout = ""

        return process

    with patch("subprocess.run", side_effect=command_response) as mock_run:
        yield mock_run


@pytest.fixture(autouse=True)
def mock_logger(monkeypatch) -> MagicMock:
    """Mock logger for all tests."""
    mock_logger = MagicMock()
    mock_logger.debug = MagicMock()
    mock_logger.info = MagicMock()
    mock_logger.warning = MagicMock()
    mock_logger.error = MagicMock()

    def mock_setup_logger(*args: Any, **kwargs: Any) -> MagicMock:
        return mock_logger

    monkeypatch.setattr("src.utils.logger.setup_logger", mock_setup_logger)
    return mock_logger


@pytest.fixture
def wifi_manager(mock_logger) -> WiFiManager:
    """Create a WiFiManager instance for testing."""
    return WiFiManager(skip_verify=True)


def pytest_configure(config: Any) -> None:
    """Register custom markers."""
    config.addinivalue_line("markers", "websocket: mark test as websocket test")
