import mpv
import asyncio
from typing import Optional
import subprocess


class AudioPlayer:
    def __init__(self):
        self._player = mpv.MPV(
            input_default_bindings=True,
            input_vo_keyboard=True,
            video=False,
            volume_max=100,
        )
        self._volume = 70
        self._is_playing = False
        self._current_url: Optional[str] = None
        self._player.volume = self._volume

    def _map_volume_to_hardware(self, volume: int) -> int:
        """Map 0-100 volume range to hardware-appropriate range."""
        # Use MPV's native 0-100 range
        return volume  # Direct mapping, no scaling

    @property
    def volume(self) -> int:
        return self._volume

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    @property
    def current_url(self) -> Optional[str]:
        return self._current_url

    async def play(self, url: str) -> None:
        try:
            self._player.play(url)
            self._is_playing = True
            self._current_url = url
        except Exception as e:
            print(f"Error playing stream: {e}")
            self._is_playing = False
            self._current_url = None
            raise

    async def stop(self) -> None:
        try:
            self._player.stop()
            self._is_playing = False
            self._current_url = None
        except Exception as e:
            print(f"Error stopping stream: {e}")
            raise

    async def set_volume(self, volume: int) -> None:
        self._volume = max(0, min(100, volume))
        try:
            self._player.volume = self._volume  # Direct volume setting
            # Set ALSA PCM volume to maximum once
            subprocess.run(
                ["amixer", "-c", "2", "sset", "PCM", "400"], capture_output=True
            )
        except Exception as e:
            print(f"Error setting volume: {e}")
            raise
