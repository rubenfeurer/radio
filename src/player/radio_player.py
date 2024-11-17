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
        if self._initialized:
            return
            
        # Initialize VLC instance
        self.instance = vlc.Instance()
        self.player = self.instance.media_player_new()
        
        # Initialize volume and status
        self.volume = 80  # Default volume
        self.current_status = {
            "state": "stopped",
            "current_station": None,
            "volume": self.volume
        }
        
        self._initialized = True
    
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
    
    def initialize(self):
        try:
            # Load config with error handling
            try:
                with open('config/config.toml', 'r') as f:
                    config = toml.load(f)
                    default_volume = config.get('default_volume', 80)
            except Exception as e:
                logger.error(f"Error loading config: {e}")
                default_volume = 80  # fallback value
            
            # VLC configuration
            vlc_args = [
                '--no-xlib',
                '--aout=alsa',
                '--alsa-audio-device=plughw:2,0',
                '--verbose=2'
            ]
            
            self.instance = vlc.Instance(' '.join(vlc_args))
            self.player = self.instance.media_player_new()
            
            # Initialize ALSA volume first
            self._init_alsa_volume()
            
            # Then set initial VLC volume from config
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
    
    def play(self, url):
        """Play a stream from the given URL"""
        try:
            # Create a new media instance
            media = self.instance.media_new(url)
            self.player.set_media(media)
            
            # Start playback
            self.player.play()
            
            # Update status
            self.current_status = {
                "state": "playing",
                "current_station": url,
                "volume": self.volume
            }
            
        except Exception as e:
            logger.error(f"Error playing stream: {e}")
            self.current_status = {
                "state": "error",
                "current_station": None,
                "volume": self.volume
            }
    
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
        try:
            return {
                "state": self.current_status["state"],
                "current_station": self.current_status["current_station"],
                "volume": self.current_status["volume"]
            }
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {
                "state": "error",
                "error": str(e)
            }
    
    def set_volume(self, volume):
        """Set volume level (0-100) for both VLC and ALSA"""
        try:
            logger.info(f"Setting volume to {volume}")
            
            # Set VLC volume
            self.player.audio_set_volume(volume)
            
            # Convert percentage to ALSA value
            if volume >= 90:  # High volume range
                alsa_value = 400  # Maximum value
            elif volume >= 70:  # Medium-high range
                alsa_value = 0   # 0 dB
            elif volume >= 50:  # Medium range
                alsa_value = -1000  # -10 dB
            else:  # Low range
                # Linear scaling for lower volumes
                alsa_value = int(-10239 + (volume * 100))
            
            # Set ALSA volume using the converted value
            cmd = ['amixer', '-c', '2', 'set', 'PCM', f'{alsa_value}']
            logger.info(f"Executing ALSA command: {' '.join(cmd)}")
            
            result = subprocess.run(cmd, 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE,
                                text=True)
            
            if result.returncode != 0:
                logger.error(f"ALSA volume command failed: {result.stderr}")
            else:
                logger.info(f"ALSA volume set successfully: {result.stdout}")
            
            self.current_status["volume"] = volume
            return True
                
        except Exception as e:
            logger.error(f"Error setting volume: {e}")
            return False
    
    def get_volume(self):
        try:
            return self.player.audio_get_volume()
        except Exception as e:
            logger.error(f"Error getting volume: {e}")
            return 0