import pytest
from unittest.mock import patch, MagicMock
import subprocess
from src.utils.wifi_manager import WiFiManager

class TestWiFiManager:
    def test_scan_networks_success(self):
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [
                MagicMock(  # get_saved_connections
                    returncode=0,
                    stdout='Salt_5GHz_D8261F:802-11-wireless\n'
                ),
                MagicMock(returncode=0),  # rescan
                MagicMock(  # wifi list
                    stdout='*:82:Salt_5GHz_D8261F:WPA2\n'
                          ':77:Salt_2GHz_D8261F:WPA2\n'
                          ':64:UETLIBERG:WPA2\n',
                    returncode=0
                )
            ]
            
            networks = WiFiManager.scan_networks()
            assert len(networks) == 3
            assert networks[0]['ssid'] == 'Salt_5GHz_D8261F'
            assert networks[0]['saved'] is True
            assert networks[0]['active'] is True

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
            mock_run.side_effect = [
                MagicMock(  # get_current_connection check
                    returncode=0,
                    stdout='no:0:OtherNetwork\n'
                ),
                MagicMock(  # connect command
                    returncode=0,
                    stdout='Device "wlan0" successfully activated.'
                )
            ]
            
            result = WiFiManager.connect_to_network('Test_Network', 'password123')
            assert result['success'] is True
            assert 'Successfully' in result['message']

    def test_disconnect_current_network_success(self):
        """Test successful network disconnection"""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [
                MagicMock(  # get_current_connection
                    returncode=0,
                    stdout='yes:90:CurrentNetwork\n'
                ),
                MagicMock(  # disconnect command
                    returncode=0,
                    stdout='Device "wlan0" successfully disconnected'
                )
            ]
            
            result = WiFiManager.disconnect_current_network()
            assert result['success'] is True
            assert 'Disconnected from CurrentNetwork' in result['message']

    def test_connect_network_timeout(self):
        with patch('subprocess.run') as mock_run:
            # Mock get_current_connection call
            mock_run.side_effect = subprocess.TimeoutExpired(['nmcli'], 30)
            
            result = WiFiManager.connect_to_network('Test_Network', 'password123')
            assert result['success'] is False
            assert 'timed out' in result['message'].lower() or 'timeout' in result['message'].lower()
            assert 'Test_Network' in result['message']  # Ensure the network name is in the error message

    def test_scan_networks_with_spaces_in_ssid(self):
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [
                MagicMock(  # get_saved_connections
                    returncode=0,
                    stdout='My Home Network:802-11-wireless\n'
                ),
                MagicMock(returncode=0),  # rescan
                MagicMock(  # wifi list
                    stdout=':70:My Home Network:WPA2\n'
                          '*:65:Another WiFi Name:WPA2\n',
                    returncode=0
                )
            ]
            
            networks = WiFiManager.scan_networks()
            assert len(networks) == 2
            assert networks[0]['ssid'] == 'My Home Network'
            assert networks[1]['ssid'] == 'Another WiFi Name'
            assert ' ' in networks[0]['ssid']  # Verify spaces are preserved

    def test_scan_networks_with_no_security(self):
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [
                MagicMock(  # get_saved_connections
                    returncode=0,
                    stdout=''
                ),
                MagicMock(returncode=0),  # rescan
                MagicMock(  # wifi list
                    stdout=':60:OpenNetwork:--\n',
                    returncode=0
                )
            ]
            
            networks = WiFiManager.scan_networks()
            assert len(networks) == 1
            assert networks[0]['ssid'] == 'OpenNetwork'
            assert networks[0]['security'] == 'none'

    def test_get_saved_connections_success(self):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                stdout='Salt_5GHz_D8261F:802-11-wireless\n'
                      'Ethernet connection 1:802-3-ethernet\n'
                      'Salt_2GHz_D8261F:802-11-wireless\n',
                returncode=0
            )
            
            saved = WiFiManager.get_saved_connections()
            assert len(saved) == 2
            assert 'Salt_5GHz_D8261F' in saved
            assert 'Salt_2GHz_D8261F' in saved
            assert 'Ethernet connection 1' not in saved  # Should only include WiFi

    def test_get_saved_connections_empty(self):
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                stdout='Ethernet connection 1:802-3-ethernet\n',
                returncode=0
            )
            
            saved = WiFiManager.get_saved_connections()
            assert len(saved) == 0

    def test_get_saved_connections_error(self):
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, 'nmcli', 'Error')
            
            saved = WiFiManager.get_saved_connections()
            assert len(saved) == 0

    def test_scan_networks_includes_saved_status(self):
        with patch('subprocess.run') as mock_run:
            # Mock saved connections call
            mock_run.side_effect = [
                MagicMock(  # get_saved_connections result
                    stdout='Salt_5GHz_D8261F:802-11-wireless\n'
                          'Salt_2GHz_D8261F:802-11-wireless\n',
                    returncode=0
                ),
                MagicMock(returncode=0),  # rescan
                MagicMock(  # scan networks result
                    stdout='*:82:Salt_5GHz_D8261F:WPA2\n'
                          ':77:Salt_2GHz_D8261F:WPA2\n'
                          ':64:UETLIBERG:WPA2\n',
                    returncode=0
                )
            ]
            
            networks = WiFiManager.scan_networks()
            assert len(networks) == 3
            
            # Check saved networks are marked correctly
            salt_5g = next(n for n in networks if n['ssid'] == 'Salt_5GHz_D8261F')
            salt_2g = next(n for n in networks if n['ssid'] == 'Salt_2GHz_D8261F')
            uetliberg = next(n for n in networks if n['ssid'] == 'UETLIBERG')
            
            assert salt_5g['saved'] is True
            assert salt_5g['active'] is True
            assert salt_2g['saved'] is True
            assert salt_2g['active'] is False
            assert uetliberg['saved'] is False
            assert uetliberg['active'] is False

    def test_connect_to_saved_network(self):
        """Test connecting to a saved network without password"""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [
                MagicMock(  # get_current_connection check
                    returncode=0,
                    stdout='no:0:OtherNetwork\n'
                ),
                MagicMock(  # connect command
                    returncode=0,
                    stdout='Connection successfully activated'
                )
            ]
            
            result = WiFiManager.connect_to_network('SavedNetwork', saved=True)
            assert result['success'] is True
            assert 'Successfully' in result['message']
            
            # Verify correct nmcli command was used
            last_call = mock_run.call_args_list[-1]
            assert last_call[0][0] == ['sudo', 'nmcli', 'connection', 'up', 'SavedNetwork']

    def test_disconnect_current_network_not_connected(self):
        """Test disconnection when no network is connected"""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [
                MagicMock(  # get_current_connection
                    returncode=0,
                    stdout='\n'
                )
            ]
            
            result = WiFiManager.disconnect_current_network()
            assert result['success'] is True
            assert 'Not connected' in result['message']

    def test_forget_network_success(self):
        """Test successfully forgetting a saved network"""
        with patch('subprocess.run') as mock_run:
            # First call checks if it's preconfigured (returns no match)
            mock_run.side_effect = [
                MagicMock(
                    returncode=1,  # Not found in preconfigured
                    stderr='Error: connection not found'
                ),
                # Second call deletes the network
                MagicMock(
                    returncode=0,
                    stdout='Connection "TestNetwork" successfully deleted.'
                )
            ]
            
            result = WiFiManager.forget_network('TestNetwork')
            assert result['success'] is True
            assert 'Successfully removed' in result['message']
            
            # Verify both calls were made with correct arguments
            calls = mock_run.call_args_list
            assert len(calls) == 2
            
            # First call should check preconfigured
            assert calls[0][0][0] == [
                'sudo', 'nmcli', '-t', '-f', '802-11-wireless.ssid',
                'connection', 'show', 'preconfigured'
            ]
            
            # Second call should delete the network
            assert calls[1][0][0] == [
                'sudo', 'nmcli', 'connection', 'delete', 'TestNetwork'
            ]

    def test_forget_network_failure(self):
        """Test failure when forgetting a network"""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                1, 'nmcli', 'Error: Connection "TestNetwork" does not exist.'
            )
            
            result = WiFiManager.forget_network('TestNetwork')
            assert result['success'] is False
            assert 'Error' in result['message']

    def test_get_saved_connections_with_preconfigured(self):
        """Test getting saved WiFi connections including preconfigured ones"""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = [
                # First call - get connections
                MagicMock(
                    returncode=0,
                    stdout='Salt_2GHz_D8261F:802-11-wireless:wlan0\n'
                          'preconfigured:802-11-wireless:--\n'
                          'Wired connection 1:802-3-ethernet:--\n'
                ),
                # Second call - get SSID of preconfigured
                MagicMock(
                    returncode=0,
                    stdout='802-11-wireless.ssid:Salt_5GHz_D8261F\n'
                )
            ]
            
            saved = WiFiManager.get_saved_connections()
            assert 'Salt_2GHz_D8261F' in saved
            assert 'Salt_5GHz_D8261F' in saved
            assert 'Wired connection 1' not in saved

    def test_forget_preconfigured_network(self):
        """Test forgetting a preconfigured network"""
        with patch('subprocess.run') as mock_run:
            # Mock all expected subprocess calls
            mock_run.side_effect = [
                # First call - check if preconfigured
                MagicMock(
                    returncode=0,
                    stdout='802-11-wireless.ssid:TestNetwork\n'
                ),
                # Second call - delete preconfigured
                MagicMock(
                    returncode=0,
                    stdout='Successfully deleted preconfigured connection.'
                ),
                # Third call - reload connections
                MagicMock(
                    returncode=0,
                    stdout=''
                )
            ]
            
            result = WiFiManager.forget_network('TestNetwork')
            assert result['success'] is True
            assert 'Successfully removed' in result['message']
            
            # Verify the correct commands were used
            calls = mock_run.call_args_list
            assert len(calls) == 3
            
            # Check preconfigured network
            assert calls[0][0][0] == [
                'sudo', 'nmcli', '-t', '-f', '802-11-wireless.ssid',
                'connection', 'show', 'preconfigured'
            ]
            
            # Delete preconfigured
            assert calls[1][0][0] == [
                'sudo', 'nmcli', 'connection', 'delete', 'preconfigured'
            ]
            
            # Reload connections
            assert calls[2][0][0] == [
                'sudo', 'nmcli', 'connection', 'reload'
            ]
  