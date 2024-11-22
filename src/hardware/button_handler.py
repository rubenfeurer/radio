from dataclasses import dataclass
from typing import Optional, Dict, ClassVar
import logging
import time
import tomli

logger = logging.getLogger(__name__)

@dataclass
class ButtonPress:
    """Represents a button press event"""
    channel: int
    button_index: int
    stream_url: Optional[str] = None

class ButtonMapper:
    """Maps GPIO channels to button indices"""
    _config: ClassVar[Dict] = None
    
    @classmethod
    def _load_config(cls) -> Dict:
        """Load button configuration from config file"""
        if cls._config is None:
            try:
                with open('config/config.toml', 'rb') as f:
                    config = tomli.load(f)
                buttons = config['gpio']['buttons']
                cls._config = {
                    buttons['button1']: 1,
                    buttons['button2']: 2,
                    buttons['button3']: 3
                }
            except Exception as e:
                logger.warning(f"Failed to load button config: {e}. Using defaults.")
                # Fallback to default values from README
                cls._config = {
                    23: 1,  # Button 1 - GPIO 23
                    24: 2,  # Button 2 - GPIO 24
                    25: 3   # Button 3 - GPIO 25
                }
        return cls._config

    @classmethod
    def get_button_index(cls, channel: int) -> Optional[int]:
        """Convert GPIO channel to button index"""
        return cls._load_config().get(channel)

class ButtonStateHandler:
    """Handles button press state and debouncing"""
    def __init__(self, debounce_time: float = 0.3):
        self.last_press_time = 0
        self.debounce_time = debounce_time

    def should_process(self) -> bool:
        """Check if enough time has passed since last press"""
        current_time = time.time()
        if current_time - self.last_press_time < self.debounce_time:
            logger.debug("Debounce check failed")
            return False
        self.last_press_time = current_time
        return True

class StreamToggler:
    """Handles stream toggling logic"""
    def __init__(self, player, stream_manager):
        self.player = player
        self.stream_manager = stream_manager

    def handle_button_press(self, button_press: ButtonPress):
        """Handle a button press event"""
        # Get stream for this button
        streams = self.stream_manager.get_streams_by_slots()
        
        # Debug logging
        logger.debug(f"Streams received: {streams}")
        logger.debug(f"Type of streams: {type(streams)}")
        
        # Convert list to dict if needed
        if isinstance(streams, list):
            streams = {i+1: stream['url'] for i, stream in enumerate(streams)}
            
        button_press.stream_url = streams.get(button_press.button_index)
        
        if not button_press.stream_url:
            logger.error(f"No stream configured for button {button_press.button_index}")
            return

        # Get current status
        current_status = self.player.get_status()
        current_state = current_status.get('state')
        current_station = current_status.get('current_station')
        
        logger.debug(f"Current state: {current_state}")
        logger.debug(f"Current station: {current_station}")
        logger.debug(f"Requested stream: {button_press.stream_url}")

        # If we're playing this stream, stop it
        if current_station == button_press.stream_url:
            logger.debug("Same stream playing - stopping")
            self.player.stop()
            # Update the status after stopping
            current_status['state'] = 'stopped'
            current_status['current_station'] = None
        else:
            # If we're playing something else, stop it first
            if current_state == 'playing':
                logger.debug("Different stream playing - stopping before switch")
                self.player.stop()
            
            # Play the requested stream
            logger.debug("Playing requested stream")
            self.player.play(button_press.stream_url)
            # Update the status after playing
            current_status['state'] = 'playing'
            current_status['current_station'] = button_press.stream_url