import pytest
from unittest.mock import patch, MagicMock
from src.app.routes import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    return app.test_client()

class TestRoutes:
    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        with patch('src.utils.wifi_manager.WiFiManager') as mock_wifi:
            mock_wifi.return_value.scan_networks.return_value = [
                {'ssid': 'Test_Network', 'signal': '80', 'security': 'WPA2', 'active': True},
                {'ssid': 'Other_Network', 'signal': '70', 'security': 'WPA2', 'active': False}
            ]
            mock_wifi.return_value.get_current_connection.return_value = {
                'ssid': 'Test_Network',
                'signal': 80,
                'connected': True
            }
            yield mock_wifi

    def test_index_route(self, client):
        response = client.get('/')
        assert response.status_code == 200

    def test_wifi_route(self, client):
        response = client.get('/wifi')
        assert response.status_code == 200
        assert b'WiFi Settings' in response.data