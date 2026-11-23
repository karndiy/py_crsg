"""Audio playback via ALSA `aplay`.

`play()` blocks until playback finishes and is only ever called one at
a time by PlaybackQueue's single consumer thread, which is what
guarantees announcements never overlap. A passive speaker must never be
wired directly to the Pi's audio output — always through a proper
amplifier (CLAUDE.md §12).
"""

from __future__ import annotations

import logging
import platform
import shutil
import subprocess
import threading
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PlaybackResult:
    success: bool
    error: Optional[str] = None


class AudioPlayer:
    def __init__(self, player_executable: str = "aplay", device: str = "default") -> None:
        self._player_executable = player_executable
        self._device = device
        self._lock = threading.Lock()
        self._current_process: Optional[subprocess.Popen] = None

    def is_available(self) -> bool:
        return platform.system() == "Linux" and shutil.which(self._player_executable) is not None

    def play(self, wav_path: str) -> PlaybackResult:
        if not self.is_available():
            message = f"{self._player_executable} is not available on this platform ({platform.system()})"
            logger.warning(message)
            return PlaybackResult(success=False, error=message)

        with self._lock:
            try:
                self._current_process = subprocess.Popen(
                    [self._player_executable, "-D", self._device, wav_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
            except OSError as exc:
                return PlaybackResult(success=False, error=str(exc))
            process = self._current_process

        _, stderr = process.communicate()

        with self._lock:
            self._current_process = None

        if process.returncode != 0:
            return PlaybackResult(success=False, error=stderr.decode("utf-8", errors="ignore"))
        return PlaybackResult(success=True)

    def stop(self) -> bool:
        with self._lock:
            if self._current_process is None:
                return False
            self._current_process.terminate()
            return True
