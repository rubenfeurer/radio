import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

import pytest
from unittest.mock import MagicMock, PropertyMock, patch

# Import WiFiManager and models before creating mocks
from src.core.wifi_manager import WiFiManager
from src.core.models import NetworkMode, NetworkModeStatus, WiFiNetwork, WiFiStatus
from config.config import settings

# Create module level mocks
mock_mpv_instance = None
mock_pi_instance = None

# Create a base WiFiManager mock
class MockWiFiManager:
    def __init__(self, *args, **kwargs):
        pass
    
    async def get_operation_mode(self):
        pass
    
    async def enable_ap_mode(self, *args, **kwargs):
        pass
    
    async def disable_ap_mode(self):
        pass
    
    async def get_ip_address(self):
        pass
    
    async def get_current_status(self):
        pass
    
    async def connect_to_network(self, ssid, password):
        pass
    
    async def _remove_connection(self, ssid):
        pass

# Create a mock instance before imports
mock_wifi_manager = MagicMock(spec=MockWiFiManager)

# Patch WiFiManager for route imports
with patch('src.core.wifi_manager.WiFiManager', return_value=mock_wifi_manager):
    from src.api.routes.ap_mode import wifi_manager as ap_wifi_manager
    from src.api.routes.wifi import wifi_manager as wifi_router_manager

@pytest.fixture
def mock_wifi_manager_ap():
    """Create a properly mocked WiFiManager instance"""
    mock = MagicMock(spec=MockWiFiManager)
    # Create new MagicMock instances for each method
    mock.get_operation_mode = MagicMock()
    mock.enable_ap_mode = MagicMock()
    mock.disable_ap_mode = MagicMock()
    mock.get_ip_address = MagicMock()
    mock.get_current_status = MagicMock()
    mock.connect_to_network = MagicMock()
    mock._remove_connection = MagicMock()
    return mock

@pytest.fixture(autouse=True)
def patch_wifi_manager(mock_wifi_manager_ap):
    """Patch WiFiManager for all tests"""
    with patch('src.api.routes.ap_mode.wifi_manager', mock_wifi_manager_ap), \
         patch('src.api.routes.wifi.wifi_manager', mock_wifi_manager_ap), \
         patch('src.core.wifi_manager.WiFiManager', return_value=mock_wifi_manager_ap):
        yield

@pytest.fixture
def wifi_manager():
    """Create a WiFiManager instance for testing"""
    with patch('src.core.wifi_manager.WiFiManager._verify_networkmanager'):
        return WiFiManager(skip_verify=True)

@pytest.fixture(autouse=True)
def mock_hardware(monkeypatch):
    """Mock hardware components for testing"""
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
        monkeypatch.setattr('mpv.MPV', mock_mpv.MPV)
        monkeypatch.setattr('pigpio.pi', mock_pigpio.pi)
        
        return {
            'mpv': mock_mpv_instance,
            'pi': mock_pi_instance
        }
    return None

# Add cleanup
@pytest.fixture(autouse=True)
def cleanup():
    yield
    global mock_mpv_instance, mock_pi_instance
    if mock_mpv_instance:
        mock_mpv_instance.reset_mock()
    if mock_pi_instance:
        mock_pi_instance.reset_mock()

@pytest.fixture
def mock_websocket():
    """Mock WebSocket for testing"""
    mock_ws = MagicMock()
    mock_ws.send = MagicMock()
    mock_ws.receive_json = MagicMock(return_value={"type": "status_request"})
    return mock_ws

@pytest.fixture
def mock_radio_manager():
    """Mock RadioManager for testing"""
    mock_manager = MagicMock()
    mock_manager.get_status.return_value = {
        "volume": 50,
        "current_station": None,
        "is_playing": False
    }
    return mock_manager

@pytest.fixture
def mock_wifi_process():
    """Create a basic WiFi process mock with success status"""
    process = MagicMock()
    process.returncode = 0
    process.stderr = ""
    process.stdout = "active"  # Default response
    return process

@pytest.fixture
def mock_networkmanager(mock_wifi_process):
    """Mock NetworkManager for WiFi testing"""
    def command_response(*args, **kwargs):
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
    
    with patch('subprocess.run', side_effect=command_response) as mock_run:
        yield mock_run

@pytest.fixture(autouse=True)
def mock_logger(monkeypatch):
    """Mock logger for all tests"""
    mock_logger = MagicMock()
    mock_logger.debug = MagicMock()
    mock_logger.info = MagicMock()
    mock_logger.warning = MagicMock()
    mock_logger.error = MagicMock()
    
    def mock_setup_logger(*args, **kwargs):
        return mock_logger
    
    monkeypatch.setattr('src.utils.logger.setup_logger', mock_setup_logger)
    return mock_logger

@pytest.fixture
def mock_ap_mode_status():
    """Create NetworkModeStatus instances for AP mode testing"""
    def create_status(mode=NetworkMode.DEFAULT, ip="192.168.1.100"):
        return NetworkModeStatus(
            mode=mode,
            ip_address=ip
        )
    return create_status

@pytest.fixture
def mock_iwlist_scan():
    """Mock iwlist scan output for AP mode testing"""
    def create_scan_output(networks=None):
        if networks is None:
            networks = [
                {"ssid": "TestNetwork1", "quality": "70/70", "security": "on"},
                {"ssid": "TestNetwork2", "quality": "50/70", "security": "off"}
            ]
            
        output = ""
        for i, network in enumerate(networks, 1):
            output += f"""
Cell {str(i).zfill(2)} - Address: 00:11:22:33:44:{str(i).zfill(2)}
                    ESSID:"{network['ssid']}"
                    Quality={network['quality']}  Signal level=-30 dBm
                    Encryption key:{network['security']}
"""
        return output
    return create_scan_output

@pytest.fixture
def mock_hostapd_process():
    """Mock hostapd process for AP mode testing"""
    process = MagicMock()
    process.returncode = 0  # Active by default
    process.stdout = "active"
    return process

@pytest.fixture
def mock_ap_mode_commands(mock_hostapd_process, mock_iwlist_scan):
    """Mock all command executions for AP mode testing"""
    def command_response(*args, **kwargs):
        command = args[0]
        process = MagicMock()
        
        if 'hostapd' in command:
            return mock_hostapd_process
        elif 'iwlist' in command and 'scan' in command:
            process.returncode = 0
            process.stdout = mock_iwlist_scan()
            return process
        elif 'iw' in command and 'scan' in command:
            process.returncode = 0
            process.stdout = """
BSS 00:11:22:33:44:55(on wlan0)
    SSID: TestNetwork1
    signal: -50.00 dBm
BSS 66:77:88:99:aa:bb(on wlan0)
    SSID: TestNetwork2
    signal: -70.00 dBm
"""
            return process
            
        process.returncode = 0
        process.stdout = ""
        return process
        
    with patch('subprocess.run', side_effect=command_response) as mock_run:
        yield mock_run

@pytest.fixture
def mock_ap_status():
    """Create WiFiStatus instances for AP mode testing"""
    def create_status(is_active=True, networks=None):
        if networks is None:
            networks = [
                WiFiNetwork(
                    ssid="TestNetwork1",
                    signal_strength=100,
                    security="WPA2",
                    in_use=False
                ),
                WiFiNetwork(
                    ssid="TestNetwork2",
                    signal_strength=71,
                    security=None,
                    in_use=False
                )
            ]
            
        return WiFiStatus(
            ssid=settings.AP_SSID if is_active else None,
            signal_strength=100 if is_active else None,
            is_connected=is_active,
            has_internet=False,
            available_networks=networks if is_active else []
        )
    return create_status