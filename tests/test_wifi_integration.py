import pytest
from unittest.mock import patch, MagicMock

@pytest.fixture
def mock_wifi_manager():
    with patch('src.utils.wifi_manager.WiFiManager') as mock:
        mock.scan_networks.return_value = [
            {'ssid': 'Test_Network', 'signal': '80', 'security': 'WPA2', 'active': True},
            {'ssid': 'Other_Network', 'signal': '70', 'security': 'WPA2', 'active': False}
        ]
        mock.get_current_connection.return_value = {
            'ssid': 'Test_Network',
            'signal': 80,
            'connected': True
        }
        mock.connect_to_network.return_value = {'success': True}
        mock.disconnect.return_value = {'success': True}
        yield mock

@pytest.fixture
def app():
    from src.app.routes import app
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    return app.test_client()

class TestWiFiIntegration:
    def test_wifi_page_loads(self, client):
        response = client.get('/wifi')
        assert response.status_code == 200
        assert b'WiFi Settings' in response.data

    def test_wifi_scan_endpoint(self, client):
        with patch('src.utils.wifi_manager.WiFiManager.scan_networks') as mock_scan:
            mock_scan.return_value = [
                {'ssid': 'Test_Network', 'signal': '80', 'security': 'WPA2', 'active': True},
                {'ssid': 'Other_Network', 'signal': '70', 'security': 'WPA2', 'active': False}
            ]
            response = client.get('/api/wifi/scan')
            assert response.status_code == 200
            data = response.get_json()
            assert 'networks' in data
            assert len(data['networks']) == 2

    def test_wifi_connect_endpoint(self, client):
        with patch('src.utils.wifi_manager.WiFiManager.connect_to_network') as mock_connect:
            mock_connect.return_value = {'success': True}
            response = client.post('/api/wifi/connect', 
                                json={'ssid': 'Test_Network', 'password': 'test123'})
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True

    def test_wifi_disconnect_endpoint(self, client):
        with patch('src.utils.wifi_manager.WiFiManager.disconnect', new_callable=MagicMock) as mock_disconnect:
            mock_disconnect.return_value = {'success': True}
            response = client.post('/api/wifi/disconnect')
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            mock_disconnect.assert_called_once()