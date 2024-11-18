import vlc
import time
import threading
import os
import signal
import logging
import requests
import subprocess
import math
import toml
import re
from pathlib import Path

logger = logging.getLogger(__name__)

class RadioPlayer:
    _instance = None
    
    def __new__(cls):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            # Initialize attributes here to avoid AttributeError
            cls._instance.initialized = False
            cls._instance.current_status = {
                'state': 'stopped',
                'current_station': None,
                'volume': 75  # Default volume
            }
            # Load config
            config_path = Path(__file__).parent.parent.parent / 'config' / 'config.toml'
            try:
                with open(config_path, 'r') as f:
                    config = toml.load(f)
                    cls._instance.current_status['volume'] = config.get('audio', {}).get('initial_volume', 75)
            except Exception as e:
                logger.error(f"Error loading config: {e}")
        return cls._instance
    
    def _get_audio_device(self):
        """Detect the audio device"""
        try:
            result = subprocess.run(['aplay', '-l'], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE,
                                  text=True)
            
            if result.returncode == 0 and result.stdout:
                # Look for Headphones in the output
                for line in result.stdout.split('\n'):
                    if 'Headphones' in line:
                        # Extract card number
                        match = re.search(r'card (\d+):', line)
                        if match:
                            return match.group(1)
                            
            logger.warning("Headphones not found, using default")
            return 'default'
            
        except Exception as e:
            logger.error(f"Error detecting audio device: {e}")
            return 'default'
    
    def __init__(self):
        """Initialize the RadioPlayer"""
        if not self.initialized:
            try:
                # Get audio device
                self.audio_card = self._get_audio_device()
                
                # Initialize VLC instance with ALSA audio output
                vlc_args = ' '.join([
                    '--aout=alsa',
                    f'--alsa-audio-device=hw:{self.audio_card},0',
                    '--verbose=2'
                ])
                self.instance = vlc.Instance(vlc_args)
                self.player = self.instance.media_player_new()
                
                # Set initial volume
                self.volume = self.current_status['volume']
                self.set_volume(self.volume)
                
                self.initialized = True
                
            except Exception as e:
                logger.error(f"Error initializing RadioPlayer: {e}")
                raise
    
    def set_volume(self, volume):
        """Set volume percentage (0-100)"""
        try:
            volume = max(0, min(100, volume))
            self.volume = volume
            
            commands = [
                ['amixer', 'sset', '-c', str(self.audio_card), 'PCM', f'{volume}%'],  # Changed order
                ['amixer', '-c', str(self.audio_card), 'sset', 'PCM', f'{volume}%'],  # Original order as fallback
                ['amixer', 'sset', 'PCM', f'{volume}%']  # Simple fallback
            ]
            
            for cmd in commands:
                logger.debug(f"Trying volume set command: {' '.join(cmd)}")
                result = subprocess.run(cmd, 
                                     stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE,
                                     text=True)
                if result.returncode == 0:
                    logger.debug(f"Volume set to {volume}%")
                    return True
                    
                logger.debug(f"Command failed: {result.stderr}")
            
            logger.error("All volume control commands failed")
            return False
                
        except Exception as e:
            logger.error(f"Error setting volume: {e}", exc_info=True)
            return False
    
    def get_volume(self):
        """Get current volume percentage"""
        try:
            commands = [
                ['amixer', '-c', str(self.audio_card), 'get', 'PCM'],
                ['amixer', 'get', 'PCM'],
                ['amixer', '-D', f'hw:CARD={self.audio_card}', 'get', 'PCM']
            ]
            
            for cmd in commands:
                logger.debug(f"Trying volume get command: {' '.join(cmd)}")
                result = subprocess.run(cmd, 
                                      stdout=subprocess.PIPE, 
                                      stderr=subprocess.PIPE,
                                      text=True)
                
                if result.returncode == 0 and 'Invalid' not in result.stderr:
                    # Parse the output to get the current percentage
                    match = re.search(r'\[(\d+)%\]', result.stdout)
                    if match:
                        volume = int(match.group(1))
                        volume = max(0, min(100, volume))
                        logger.debug(f"Got volume: {volume}%")
                        return volume
                
                logger.debug(f"Command failed: {result.stderr}")
            
            logger.error("Failed to get volume from any command")
            return self.volume  # Return last known volume as fallback
                
        except Exception as e:
            logger.error(f"Error getting volume: {e}", exc_info=True)
            return self.volume  # Return last known volume as fallback
    
    def get_status(self):
        """Get current player status"""
        return self.current_status.copy()  # Return a copy to prevent external modification
    
    def play(self, url):
        """Play a stream URL"""
        try:
            # Create a new media
            media = self.instance.media_new(url)
            self.player.set_media(media)
            
            # Attempt to play
            if self.player.play() == 0:
                self.current_status['state'] = 'playing'
                self.current_status['current_station'] = url
                logger.info(f"Playing stream: {url}")
                return True
            else:
                logger.error("Failed to play stream")
                return False
                
        except Exception as e:
            logger.error(f"Error playing stream: {e}")
            return False
    
    def stop(self):
        """Stop the current playback"""
        try:
            self.player.stop()
            self.current_status['state'] = 'stopped'
            self.current_status['current_station'] = None
            logger.info("Playback stopped")
            return True
        except Exception as e:
            logger.error(f"Error stopping playback: {e}")
            return False
    
    def _handle_volume_change(self, volume_delta):
        """Handle volume change from rotary encoder"""
        try:
            new_volume = max(0, min(100, self.volume + volume_delta))
            logger.debug(f"Attempting to change volume from {self.volume} to {new_volume}")
            if self.set_volume(new_volume):
                logger.info(f"Volume changed to {new_volume}")
            else:
                logger.error(f"Failed to change volume to {new_volume}")
        except Exception as e:
            logger.error(f"Error in volume change handler: {e}", exc_info=True)