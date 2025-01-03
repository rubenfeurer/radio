import subprocess
from typing import Optional

import mpv


class AudioPlayer:
    def __init__(self, status_update_callback=None) -> None:
        # Initialize system audio
        subprocess.run(["amixer", "sset", "Master", "unmute"], check=False)

        self._player = mpv.MPV(
            input_default_bindings=True,
            input_vo_keyboard=True,
            video=False,
            volume_max=100,
        )
        self._volume: int = 70
        self._is_playing: bool = False
        self._current_url: Optional[str] = None
        self._player.volume = self._volume
        self._status_callback = status_update_callback

    async def play_stream(self, url: str) -> None:
        """Play an audio stream"""
        try:
            self._player.play(url)
            self._current_url = url
            self._is_playing = True
            if self._status_callback:
                await self._status_callback({"is_playing": True})
        except Exception as e:
            print(f"Error playing stream: {e}")
            self._is_playing = False

    async def stop_stream(self) -> None:
        """Stop the current stream"""
        try:
            self._player.stop()
            self._current_url = None
            self._is_playing = False
            if self._status_callback:
                await self._status_callback({"is_playing": False})
        except Exception as e:
            print(f"Error stopping stream: {e}")

    async def set_volume(self, volume: int) -> None:
        """Set the audio volume"""
        try:
            self._volume = max(0, min(100, volume))
            self._player.volume = self._volume
            if self._status_callback:
                await self._status_callback({"volume": self._volume})
        except Exception as e:
            print(f"Error setting volume: {e}")
