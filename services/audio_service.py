"""Business logic behind the /api/v1/audio endpoints.

Device listing and the "test tone" action run directly in whichever
process calls them (normally the web process, from the dashboard). The
serialized announcement-playback queue lives in the worker process and
is intentionally not reused here — a manual speaker test is a
diagnostic action, not a community announcement, so it is allowed to
run independently (and could in principle overlap with an in-progress
announcement if triggered at the same moment).
"""

from __future__ import annotations

from typing import Dict, List

from flask import current_app

from modules.audio.audio_player import AudioPlayer, PlaybackResult
from modules.audio.device_manager import AudioDevice, list_audio_devices


def get_devices() -> List[AudioDevice]:
    return list_audio_devices()


def get_status() -> Dict[str, object]:
    devices = list_audio_devices()
    player = _build_player()
    return {
        "player_available": player.is_available(),
        "configured_player": current_app.config["AUDIO_PLAYER"],
        "configured_device": current_app.config["AUDIO_DEVICE"],
        "devices_detected": len(devices),
    }


def test_playback(wav_path: str) -> PlaybackResult:
    return _build_player().play(wav_path)


def _build_player() -> AudioPlayer:
    return AudioPlayer(
        player_executable=current_app.config["AUDIO_PLAYER"],
        device=current_app.config["AUDIO_DEVICE"],
    )
