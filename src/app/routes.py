import os
import signal
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, request, jsonify, send_from_directory, render_template, make_response
from src.player.radio_player import RadioPlayer
from src.utils.stream_manager import StreamManager
from src.utils.state_manager import StateManager
import toml
import json
from src.app.radio_service import RadioService
from src.utils.wifi_manager import WiFiManager
from src.app import app  # This is causing the circular import

# Set up logging with more detail and rotation
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            'logs/radio.log',
            maxBytes=1024 * 1024,  # 1MB per file
            backupCount=5,         # Keep 5 backup files
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
        # First try to load from radio_state.json
        with open('config/radio_state.json', 'r') as f:
            state = json.load(f)
            selected_stations = state.get('selected_stations', [])
            
        # If no stations in state, load defaults from config.toml
        if not selected_stations:
            with open('config/config.toml', 'r') as f:
                config = toml.load(f)
                default_stations = config.get('default_stations', [])
                logger.info(f"Default stations from config: {default_stations}")
                
            # Get all available streams
            all_streams = load_streams()
            logger.info(f"Available streams: {[s['name'] for s in all_streams]}")
            
            # Convert default station names to full station objects
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

@app.route('/api/status')
def status():
    try:
        status_data = radio_service.player.get_status()
        logger.info(f"Status request - returning: {status_data}")
        return jsonify(status_data)
    except Exception as e:
        logger.error(f"Error in status endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/play', methods=['POST'])
def play():
    try:
        data = request.get_json()
        logger.info(f"Play request received with data: {data}")
        
        if not data or 'url' not in data:
            logger.error("Missing url parameter")
            return jsonify({"error": "Missing url parameter"}), 400
        
        url = data['url']
        logger.info(f"Attempting to play URL: {url}")
        
        # Test if URL is accessible
        try:
            import requests
            response = requests.head(url, timeout=5)
            logger.info(f"URL test response: {response.status_code}")
        except Exception as e:
            logger.error(f"URL test failed: {e}")
        
        success = radio_service.player.play(url)
        
        if success:
            logger.info("Successfully started playback")
            status = radio_service.player.get_status()
            logger.info(f"Player status after play: {status}")
            return jsonify(status)
        else:
            logger.error("Failed to play stream")
            return jsonify({"error": "Failed to play stream"}), 500
    except Exception as e:
        logger.error(f"Error in play endpoint: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/stop', methods=['POST'])
def stop():
    try:
        success = radio_service.player.stop()
        if success:
            return jsonify(radio_service.player.get_status())
        else:
            return jsonify({"error": "Failed to stop playback"}), 500
    except Exception as e:
        logger.error(f"Error in stop endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/volume', methods=['POST'])
def volume():
    try:
        data = request.get_json()
        if not data or 'volume' not in data:
            return jsonify({"error": "Missing volume parameter"}), 400
        
        volume = int(data['volume'])
        if volume < 0 or volume > 100:
            return jsonify({"error": "Volume must be between 0 and 100"}), 400
            
        success = radio_service.player.set_volume(volume)
        if success:
            return jsonify(radio_service.player.get_status())
        else:
            return jsonify({"error": "Failed to set volume"}), 500
    except Exception as e:
        logger.error(f"Error in volume endpoint: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/')
def index():
    try:
        # Load all streams
        streams = load_streams()
        # Load selected stations
        selected_stations = load_selected_stations()
        
        # If no stations are selected, use the first few streams as defaults
        if not selected_stations:
            selected_stations = streams[:3] if streams else []
        
        return render_template('index.html', stations=selected_stations)
    except Exception as e:
        logger.error(f"Error in index route: {e}")
        return render_template('index.html', stations=[])

@app.route('/stations/<int:slot_index>')
def stations(slot_index):
    try:
        streams = load_streams()
        logger.info(f"Loaded {len(streams)} streams for slot {slot_index}")
        return render_template('stations.html', 
                             streams=streams, 
                             slot_index=slot_index)
    except Exception as e:
        logger.error(f"Error in stations route: {e}")
        return render_template('stations.html', 
                             streams=[], 
                             slot_index=slot_index)

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

@app.route('/api/select_station', methods=['POST'])
def select_station():
    try:
        data = request.get_json()
        if not data or 'name' not in data or 'slot' not in data:
            return jsonify({"success": False, "error": "Missing parameters"}), 400
        
        # Load current state
        try:
            with open('config/radio_state.json', 'r') as f:
                state = json.load(f)
        except:
            state = {"selected_stations": []}
        
        # Load all streams
        streams = load_streams()
        
        # Find the selected stream
        selected_stream = next((s for s in streams if s['name'] == data['name']), None)
        if not selected_stream:
            return jsonify({"success": False, "error": "Stream not found"}), 404
        
        # Update the selected stations
        while len(state['selected_stations']) <= data['slot']:
            state['selected_stations'].append(None)
        state['selected_stations'][data['slot']] = selected_stream
        
        # Save the state
        with open('config/radio_state.json', 'w') as f:
            json.dump(state, f, indent=4)
        
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error in select_station endpoint: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

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

if __name__ == '__main__':
    try:
        logger.info("Starting Flask application...")
        app.run(host='0.0.0.0', port=5000)
    except Exception as e:
        logger.error(f"Error running app: {e}")
        radio_service.cleanup()
        raise