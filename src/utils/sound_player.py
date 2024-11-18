import vlc
import os
import logging
import time

logger = logging.getLogger(__name__)

class SoundPlayer:
    def __init__(self):
        self.sound_dir = "/home/radio/internetRadio/sounds"
        self.instance = vlc.Instance('--aout=alsa')
        self.player = self.instance.media_player_new()
        
    def play_sound(self, sound_file, wait=True):
        """Play a sound file from the sounds directory
        Args:
            sound_file (str): Name of the sound file
            wait (bool): Whether to wait for sound to finish
        """
        try:
            sound_path = os.path.join(self.sound_dir, sound_file)
            if os.path.exists(sound_path):
                media = self.instance.media_new(sound_path)
                self.player.set_media(media)
                self.player.play()
                
                if wait:
                    # Wait max 2 seconds for sound to finish
                    start_time = time.time()
                    time.sleep(0.1)  # Initial wait for playback to start
                    while self.player.is_playing() and (time.time() - start_time) < 2:
                        time.sleep(0.1)
            else:
                logger.error(f"Sound file not found: {sound_path}")
        except Exception as e:
            logger.error(f"Error playing sound: {e}") 