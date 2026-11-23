"""ALSA audio device discovery via `aplay -l`.

On a non-Linux development machine (no ALSA) this returns an empty list
with a warning instead of fabricating devices — CLAUDE.md explicitly
forbids reporting hardware capability that hasn't actually been
verified on the target device.
"""

from __future__ import annotations

import logging
import platform
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)

_CARD_LINE_RE = re.compile(r"^card (\d+): (\S+) \[(.*?)\], device (\d+): (.*)$")


@dataclass
class AudioDevice:
    card: int
    device: int
    name: str
    description: str


def list_audio_devices() -> List[AudioDevice]:
    if platform.system() != "Linux" or shutil.which("aplay") is None:
        logger.warning("aplay/ALSA not available on this platform; cannot list audio devices")
        return []

    try:
        result = subprocess.run(["aplay", "-l"], capture_output=True, timeout=5, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.error("Failed to run aplay -l: %s", exc)
        return []

    devices: List[AudioDevice] = []
    for line in result.stdout.decode("utf-8", errors="ignore").splitlines():
        match = _CARD_LINE_RE.match(line.strip())
        if match:
            devices.append(
                AudioDevice(
                    card=int(match.group(1)),
                    device=int(match.group(4)),
                    name=match.group(2),
                    description=f"{match.group(3)} / {match.group(5)}",
                )
            )
    return devices
