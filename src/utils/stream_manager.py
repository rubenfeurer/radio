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
    
    def get_streams_by_slots(self):
        """Get the streams configured in radio_state.json"""
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
                return state.get('selected_stations', [])
        except Exception as e:
            logger.error(f"Error loading radio state: {e}")
            # Fallback to first three streams if state file can't be read
            return self.streams[:3] if self.streams else []