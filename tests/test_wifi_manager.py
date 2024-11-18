import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.wifi_manager import WiFiManager

class TestWiFiManager:
    def test_scan_networks_success(self):
        with patch('subprocess.run') as mock_run:
            # Mock the current connection call
            mock_run.side_effect = [
                # First call for current connection
                MagicMock(stdout='''
                    wlan0     IEEE 802.11  ESSID:"MyNetwork"
                    Quality=70/70  Signal level=-30 dBm
                '''),
                # Second call for iwlist scan
                MagicMock(returncode=0),
                # Third call for nmcli device wifi list
                MagicMock(
                    stdout='MyNetwork:80:WPA2:****\nOtherNetwork:70:WPA2:***\nThirdNetwork:60:WPA2:**',
                    returncode=0
                )
            ]
            
            networks = WiFiManager.scan_networks()
            assert len(networks) == 3
            assert networks[0]['ssid'] == 'MyNetwork'
            assert networks[0]['signal'] == '80'
            assert networks[0]['active'] == True

    def test_get_current_connection_success(self):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                stdout='''
                wlan0     IEEE 802.11  ESSID:"MyNetwork"
                          Quality=70/70  Signal level=-30 dBm
                '''
            )
            result = WiFiManager.get_current_connection()
            assert result == {
                'ssid': 'MyNetwork',
                'signal': 100,
                'connected': True
            }

    def test_connect_to_network_success(self):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='Successfully activated connection.'
            )
            result = WiFiManager.connect_to_network('Test_Network', 'password123')
            assert result['success'] is True

    def test_connect_to_network_failure(self):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stderr='Error: Connection activation failed: Incorrect password'
            )
            result = WiFiManager.connect_to_network('Test_Network', 'wrong_password')
            assert result['success'] is False
            assert 'password' in result['error'].lower()

    def test_disconnect_success(self):
        with patch('subprocess.run') as mock_run, \
             patch('src.utils.wifi_manager.WiFiManager.get_current_connection') as mock_current:
            
            # Mock current connection
            mock_current.return_value = {
                'ssid': 'Test_Network',
                'signal': 80,
                'connected': True
            }
            
            # Mock successful disconnect
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Device 'wlan0' successfully disconnected."
            )
            
            result = WiFiManager.disconnect()
            assert result['success'] is True
            mock_run.assert_called_once_with(
                ['sudo', 'nmcli', 'device', 'disconnect', 'wlan0'],
                capture_output=True,
                text=True,
                timeout=10
            )

    def test_disconnect_not_connected(self):
        with patch('src.utils.wifi_manager.WiFiManager.get_current_connection') as mock_current:
            mock_current.return_value = None
            result = WiFiManager.disconnect()
            assert result['success'] is False
            assert 'Not connected' in result['error']

    def test_disconnect_failure(self):
        with patch('subprocess.run') as mock_run, \
             patch('src.utils.wifi_manager.WiFiManager.get_current_connection') as mock_current:
            
            # Mock current connection
            mock_current.return_value = {
                'ssid': 'Test_Network',
                'signal': 80,
                'connected': True
            }
            
            # Mock failed disconnect
            mock_run.return_value = MagicMock(
                returncode=1,
                stderr='Error: Device not found'
            )
            
            result = WiFiManager.disconnect()
            assert result['success'] is False
            assert 'Device not found' in result['error']
  