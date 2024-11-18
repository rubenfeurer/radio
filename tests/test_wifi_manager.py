import pytest
from unittest.mock import patch, MagicMock
import subprocess
from src.utils.wifi_manager import WiFiManager

class TestWiFiManager:
    def test_scan_networks_success(self):
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # rescan
                MagicMock(
                    stdout='*:82:Salt_5GHz_D8261F:WPA2\n'
                          ':77:Salt_2GHz_D8261F:WPA2\n'
                          ':64:UETLIBERG:WPA2\n',
                    returncode=0
                )
            ]
            
            networks = WiFiManager.scan_networks()
            assert len(networks) == 3
            assert networks[0] == {
                'ssid': 'Salt_5GHz_D8261F',
                'signal': 82,
                'security': 'WPA2',
                'active': True
            }

    def test_scan_networks_empty(self):
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # rescan
                MagicMock(stdout='', returncode=0)
            ]
            
            networks = WiFiManager.scan_networks()
            assert len(networks) == 0

    def test_scan_networks_error(self):
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = Exception("Network scan failed")
            
            networks = WiFiManager.scan_networks()
            assert len(networks) == 0

    def test_get_current_connection_success(self):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                stdout='yes:90:Network1\nno:80:Network2\n',
                returncode=0
            )
            
            result = WiFiManager.get_current_connection()
            assert result == {
                'ssid': 'Network1',
                'signal': 90,
                'connected': True
            }

    def test_connect_to_network_success(self):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='Device "wlan0" successfully activated.'
            )
            
            result = WiFiManager.connect_to_network('Test_Network', 'password123')
            assert result['success'] is True
            assert 'successfully' in result['message']

    def test_disconnect_success(self):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='Device "wlan0" successfully disconnected.'
            )
            
            result = WiFiManager.disconnect()
            assert result['success'] is True
            assert 'successfully' in result['message']

    def test_connect_network_timeout(self):
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(['nmcli'], 30)
            
            result = WiFiManager.connect_to_network('Test_Network', 'password123')
            assert result['success'] is False
            assert 'timeout' in result['message'].lower()

    def test_scan_networks_with_spaces_in_ssid(self):
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # rescan
                MagicMock(
                    stdout=':70:My Home Network:WPA2\n'
                          '*:65:Another WiFi Name:WPA2\n',
                    returncode=0
                )
            ]
            
            networks = WiFiManager.scan_networks()
            assert len(networks) == 2
            assert networks[0] == {
                'ssid': 'My Home Network',
                'signal': 70,
                'security': 'WPA2',
                'active': False
            }
            assert networks[1] == {
                'ssid': 'Another WiFi Name',
                'signal': 65,
                'security': 'WPA2',
                'active': True
            }

    def test_scan_networks_with_no_security(self):
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0),  # rescan
                MagicMock(
                    stdout=':60:OpenNetwork:--\n',
                    returncode=0
                )
            ]
            
            networks = WiFiManager.scan_networks()
            assert len(networks) == 1
            assert networks[0] == {
                'ssid': 'OpenNetwork',
                'signal': 60,
                'security': 'none',
                'active': False
            }
  