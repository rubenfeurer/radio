import tomli
import json
import logging

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