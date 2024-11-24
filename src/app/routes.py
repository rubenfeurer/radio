import os
import signal
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, request, jsonify, send_from_directory, render_template
from src.player.radio_player import RadioPlayer
from src.utils.stream_manager import StreamManager
from src.utils.state_manager import StateManager
import toml
import json
from src.app.radio_service import RadioService
from src.utils.wifi_manager import WiFiManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            'logs/radio.log',
            maxBytes=1024 * 1024,
            backupCount=5,
            encoding='utf-8'
        ),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global service instance
try:
    logger.info("Creating global RadioService instance")
    radio_service = RadioService()
    logger.info("RadioService created successfully")
except Exception as e:
    logger.error(f"Failed to create RadioService: {e}")
    raise

def signal_handler(sig, frame):
    logger.info("Received shutdown signal")
    radio_service.cleanup()
    os._exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def load_streams():
    try:
        with open('config/streams.toml', 'r') as f:
            config = toml.load(f)
            return config.get('links', [])
    except Exception as e:
        logger.error(f"Error loading streams: {e}")
        return []

def load_selected_stations():
    try:
        with open('config/radio_state.json', 'r') as f:
            state = json.load(f)
            selected_stations = state.get('selected_stations', [])
            
        if not selected_stations:
            with open('config/config.toml', 'r') as f:
                config = toml.load(f)
                default_stations = config.get('default_stations', [])
                logger.info(f"Default stations from config: {default_stations}")
                
            all_streams = load_streams()
            logger.info(f"Available streams: {[s['name'] for s in all_streams]}")
            
            selected_stations = []
            for station_name in default_stations:
                station = next((s for s in all_streams if s['name'] == station_name), None)
                if station:
                    selected_stations.append(station)
                else:
                    logger.warning(f"Station not found: {station_name}")
            
        logger.info(f"Final selected stations: {[s['name'] for s in selected_stations]}")
        return selected_stations
            
    except Exception as e:
        logger.error(f"Error loading selected stations: {e}")
        return load_default_stations()

def load_default_stations():
    try:
        with open('config/config.toml', 'r') as f:
            config = toml.load(f)
            default_stations = config.get('default_stations', [])
            
        all_streams = load_streams()
        return [s for s in all_streams if s['name'] in default_stations]
    except Exception as e:
        logger.error(f"Error loading default stations: {e}")
        return []

def register_routes(app):
    @app.route('/api/status')
    def status():
        try:
            status_data = radio_service.player.get_status()
            logger.info(f"Status request - returning: {status_data}")
            return jsonify(status_data)
        except Exception as e:
            logger.error(f"Error in status endpoint: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route('/wifi')
    def wifi():
        current = WiFiManager.get_current_connection()
        networks = WiFiManager.scan_networks()
        
        logger.info(f"Current connection: {current}")
        logger.info(f"Available networks: {networks}")
        
        return render_template('wifi.html', current=current, networks=networks)

    @app.route('/api/wifi/scan')
    def wifi_scan():
        """API endpoint to scan for WiFi networks"""
        networks = WiFiManager.scan_networks()
        return jsonify({'networks': networks})

    @app.route('/api/wifi/connect', methods=['POST'])
    def connect_wifi():
        data = request.get_json()
        ssid = data.get('ssid')
        password = data.get('password')
        saved = data.get('saved', False)
        
        if not ssid:
            return jsonify({'success': False, 'message': 'SSID is required'})
        
        if not saved and not password:
            return jsonify({'success': False, 'message': 'Password is required for unsaved networks'})
        
        result = WiFiManager.connect_to_network(ssid, password, saved)
        return jsonify(result)

    @app.route('/api/wifi/disconnect', methods=['POST'])
    def disconnect_wifi():
        result = WiFiManager.disconnect_current_network()
        return jsonify(result)

    @app.route('/api/wifi/status')
    def wifi_status():
        """API endpoint to get current WiFi status"""
        current = WiFiManager.get_current_connection()
        return jsonify({'current': current})

    @app.route('/api/wifi/forget', methods=['POST'])
    def forget_wifi():
        data = request.get_json()
        ssid = data.get('ssid')
        
        if not ssid:
            return jsonify({'success': False, 'message': 'SSID is required'})
        
        result = WiFiManager.forget_network(ssid)
        return jsonify(result)

    return app

if __name__ == '__main__':
    from src.app import app
    try:
        logger.info("Starting Flask application...")
        app.run(host='0.0.0.0', port=5000)
    except Exception as e:
        logger.error(f"Error running app: {e}")
        radio_service.cleanup()
        raise