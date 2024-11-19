import pytest
from unittest.mock import patch, MagicMock
from src.app import app
from src.utils.wifi_manager import WiFiManager

class TestRoutes:
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test client before each test"""
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        yield
        self.ctx.pop()

    def test_wifi_route_with_networks(self):
        mock_data = {
            'current': {
                'ssid': 'CurrentNetwork',
                'signal': 90,
                'security': 'WPA2',
                'active': True
            },
            'networks': [
                {'ssid': 'Network1', 'signal': 80, 'security': 'WPA2', 'active': False},
                {'ssid': 'Network2', 'signal': 70, 'security': 'WPA2', 'active': False}
            ]
        }
        
        # Mock both class methods correctly
        with patch.object(WiFiManager, 'get_current_connection', return_value=mock_data['current']), \
             patch.object(WiFiManager, 'scan_networks', return_value=mock_data['networks']):
            
            response = self.client.get('/wifi')
            assert response.status_code == 200
            assert b'CurrentNetwork' in response.data
            assert b'Network1' in response.data
            assert b'Network2' in response.data

    def test_connect_saved_network(self):
        """Test connecting to a saved network without password"""
        with patch.object(WiFiManager, 'connect_to_network') as mock_connect:
            mock_connect.return_value = {'success': True, 'message': 'Connected to SavedNetwork'}
            
            response = self.client.post('/api/wifi/connect', 
                json={'ssid': 'SavedNetwork', 'saved': True})
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            mock_connect.assert_called_once_with('SavedNetwork', None, True)

    def test_disconnect_network(self):
        """Test disconnecting from current network"""
        with patch.object(WiFiManager, 'disconnect_current_network') as mock_disconnect:
            mock_disconnect.return_value = {'success': True, 'message': 'Disconnected'}
            
            response = self.client.post('/api/wifi/disconnect')
            
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True
            mock_disconnect.assert_called_once()