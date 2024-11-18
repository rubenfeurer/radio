import tomli
import tomli_w
import logging
import requests
import json
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class StreamManager:
    def __init__(self, toml_file='config/streams.toml', state_file='config/radio_state.json'):
        self.toml_file = toml_file
        self.state_file = state_file
        self.streams = self.load_streams()
        
    def load_streams(self):
        """Load all streams from the TOML file"""
        try:
            with open(self.toml_file, 'rb') as f:
                data = tomli.load(f)
                return data.get('links', [])
        except Exception as e:
            logger.error(f"Error loading streams: {e}")
            return []
    
    def load_radio_state(self):
        """Load radio state from JSON file"""
        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Radio state file not found: {self.state_file}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in radio state file: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading radio state: {e}")
            return None
    
    def get_streams_by_slots(self):
        """Get streams mapped to their slot numbers"""
        try:
            state = self.load_radio_state()
            if state and 'selected_stations' in state:
                # Convert list to dictionary with 1-based indices
                return {i+1: station['url'] 
                       for i, station in enumerate(state['selected_stations'])}
            # If no state file or no selected stations, fall back to streams from TOML
            return {i+1: stream['url'] 
                    for i, stream in enumerate(self.streams[:3])}  # Limit to first 3 streams
        except Exception as e:
            logger.error(f"Error getting streams by slots: {e}")
            return {}
    
    def validate_stream_url(self, url: str) -> bool:
        """Validate if a stream URL is accessible"""
        if not url.startswith(('http://', 'https://')):
            return False
        try:
            response = requests.head(url, timeout=5)
            return response.status_code == 200
        except (requests.RequestException, ValueError):
            return False
    
    def save_stream_config(self, stream: Dict[str, str], slot: int) -> bool:
        """Save stream configuration to a specific slot"""
        try:
            # Get existing state or create new
            state = self.load_radio_state() or {"selected_stations": []}
            
            # Ensure selected_stations list is long enough
            while len(state["selected_stations"]) < slot:
                state["selected_stations"].append(None)
            
            # Update the stream for the given slot (1-based to 0-based index)
            state["selected_stations"][slot-1] = stream
            
            # Save the updated configuration
            with open(self.state_file, 'w') as f:
                json.dump(state, f)
            return True
        except Exception as e:
            logger.error(f"Error saving stream config: {e}")
            return False