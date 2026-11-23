"""WAV inspection used to validate a generated file before it is handed
to the playback queue (CLAUDE.md §11 requirement #6).
"""

from __future__ import annotations

import wave
from dataclasses import dataclass
from typing import Optional


@dataclass
class WavInfo:
    valid: bool
    duration_seconds: Optional[float] = None
    error: Optional[str] = None


def inspect_wav(path: str) -> WavInfo:
    try:
        with wave.open(path, "rb") as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            duration = (frames / float(rate)) if rate else None
            return WavInfo(valid=True, duration_seconds=duration)
    except (wave.Error, FileNotFoundError, EOFError, OSError) as exc:
        return WavInfo(valid=False, error=str(exc))
