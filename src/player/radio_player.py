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

logger = logging.getLogger(__name__)

class RadioPlayer:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RadioPlayer, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the radio player"""
        try:
            # Create VLC instance with custom audio output
            self.instance = vlc.Instance('--aout=alsa')  # Use ALSA instead of PulseAudio
            self.player = self.instance.media_player_new()
            self.volume = 80  # Default volume
            self.player.audio_set_volume(self.volume)
            logger.info("Radio player initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing radio player: {e}")
            raise
        self.current_status = {
            'state': 'stopped',
            'current_station': None,
            'volume': self.volume
        }
    
    def _init_alsa_volume(self):
        """Initialize ALSA volume settings"""
        try:
            logger.info("Initializing ALSA volume settings")
            
            # Set initial ALSA volume to maximum
            cmd = ['amixer', '-c', '2', 'set', 'PCM', '400']  # 400 is max value for this device
            logger.info(f"Executing ALSA command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE,
                                text=True)
            
            if result.returncode != 0:
                logger.error(f"ALSA command failed: {result.stderr}")
            else:
                logger.info(f"ALSA volume initialized: {result.stdout}")
                
        except Exception as e:
            logger.error(f"Error initializing ALSA volume: {e}")
    
    def get_vlc_args(self):
        """Get VLC arguments for testing"""
        return [
            '--no-xlib',
            '--aout=alsa',
            '--alsa-audio-device=plughw:2,0'
        ]
    
    def get_vlc_configuration(self):
        """Get VLC configuration string"""
        return '--no-xlib --aout=alsa --alsa-audio-device=plughw:2,0'
    
    def initialize(self):
        """Initialize the VLC player with ALSA output"""
        try:
            # Load config
            try:
                with open('config/config.toml', 'r') as f:
                    config = toml.load(f)
                    default_volume = config.get('default_volume', 80)
            except Exception as e:
                logger.error(f"Error loading config: {e}")
                default_volume = 80
            
            # Initialize VLC with ALSA
            vlc_config = '--no-xlib --aout=alsa --alsa-audio-device=plughw:2,0'
            self.instance = vlc.Instance(vlc_config)
            self.player = self.instance.media_player_new()
            
            # Set initial volume through ALSA
            self.volume = default_volume
            self.set_volume(default_volume)
            
            logger.info(f"Player initialized with ALSA output and volume {default_volume}")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing player: {e}")
            return False
    
    def _signal_handler(self, signum, frame):
        self.cleanup()
    
    def cleanup(self):
        try:
            if hasattr(self, 'player') and self.player:
                self.player.stop()
                del self.player
            if hasattr(self, 'instance') and self.instance:
                del self.instance
        except:
            pass
        finally:
            # Force kill any remaining VLC processes
            os.system("pkill vlc")
    
    def play(self, url: str) -> None:
        """Play the given URL"""
        try:
            # Stop any currently playing stream
            self.stop()
            
            # Add retry logic for initial connection
            max_retries = 3
            retry_delay = 1.5  # Increased from 1 to 1.5 seconds
            initial_buffer = 2.0  # Added initial buffer time
            
            for attempt in range(max_retries):
                try:
                    # Create new media and set it
                    media = self.instance.media_new(url)
                    self.player.set_media(media)
                    
                    # Attempt to play
                    result = self.player.play()
                    
                    # Wait for initial buffering
                    time.sleep(initial_buffer)
                    
                    # Check multiple times for playback status
                    check_attempts = 3
                    for _ in range(check_attempts):
                        if self.player.is_playing():
                            logging.info(f"Successfully started playing {url} on attempt {attempt + 1}")
                            # Update current status
                            self.current_status = {
                                'state': 'playing',
                                'current_station': url,
                                'volume': self.volume
                            }
                            return
                        time.sleep(0.5)
                    
                    if attempt < max_retries - 1:
                        logging.warning(f"Failed to start playback on attempt {attempt + 1}, retrying...")
                        time.sleep(retry_delay)
                        self.stop()  # Ensure clean state before retry
                    
                except Exception as e:
                    if attempt < max_retries - 1:
                        logging.warning(f"Connection error on attempt {attempt + 1}: {str(e)}, retrying...")
                        time.sleep(retry_delay)
                        self.stop()  # Ensure clean state before retry
                    else:
                        raise
            
            logging.error(f"Failed to start playback after {max_retries} attempts")
            self.current_status = {
                'state': 'stopped',
                'current_station': None,
                'volume': self.volume
            }
            raise RuntimeError(f"Failed to start playback of {url} after {max_retries} attempts")
            
        except Exception as e:
            logging.error(f"Error playing URL {url}: {str(e)}")
            self.current_status = {
                'state': 'stopped',
                'current_station': None,
                'volume': self.volume
            }
            raise
    
    def stop(self):
        """Stop the current stream"""
        if self.player:
            self.player.stop()
            self.current_status = {
                "state": "stopped",
                "current_station": None,
                "volume": self.volume
            }
    
    def is_playing(self):
        return bool(self.player.is_playing())
    
    def get_current_stream(self):
        return self.current_url
    
    def get_status(self):
        """Get the current status of the player"""
        try:
            self.current_status['volume'] = self.volume
            return self.current_status
        except Exception as e:
            self.logger.error(f"Error getting status: {str(e)}")
            return None
    
    def set_volume(self, volume):
        """Set volume using ALSA"""
        try:
            # Ensure volume is within bounds
            volume = max(0, min(100, volume))
            
            # Set ALSA volume
            cmd = ['amixer', '-c', '2', 'set', 'PCM', f'{volume}%']
            result = subprocess.run(cmd, 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE,
                                  text=True)
            
            if result.returncode == 0:
                self.volume = volume
                logger.info(f"Volume set to {volume}%")
                return True
            else:
                logger.error(f"Failed to set volume: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Error setting volume: {e}")
            return False
    
    def get_volume(self):
        """Get current volume from ALSA"""
        try:
            cmd = ['amixer', '-c', '2', 'get', 'PCM']
            result = subprocess.run(cmd, 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE,
                                text=True)
            
            if result.returncode == 0:
                # Parse the volume value from amixer output
                import re
                match = re.search(r'\[(\d+)%\]', result.stdout)
                if match:
                    return int(match.group(1))
            
            # Return stored volume if we can't get it from ALSA
            return self.volume
            
        except Exception as e:
            logger.error(f"Error getting volume: {e}")
            return self.volume
    
    def _setup_audio(self):
        """Configure audio output"""
        try:
            instance = vlc.Instance('--aout=alsa')
            if not instance:
                instance = vlc.Instance()  # Fallback to default
            return instance
        except Exception as e:
            logger.warning(f"Failed to setup ALSA audio: {e}, falling back to default")
            return vlc.Instance()