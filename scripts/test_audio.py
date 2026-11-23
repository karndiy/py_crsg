"""Manual test: list ALSA devices and optionally play a WAV file. Run
on the target Raspberry Pi.

Usage: python scripts/test_audio.py [path/to/file.wav]
"""

from __future__ import annotations

import sys

from config import Config
from modules.audio.audio_player import AudioPlayer
from modules.audio.device_manager import list_audio_devices


def main() -> None:
    devices = list_audio_devices()
    if not devices:
        print("No audio devices detected.")
    for d in devices:
        print(f"card {d.card}: {d.name} [{d.description}], device {d.device}")

    if len(sys.argv) > 1:
        wav_path = sys.argv[1]
        player = AudioPlayer(player_executable=Config.AUDIO_PLAYER, device=Config.AUDIO_DEVICE)
        result = player.play(wav_path)
        print("Playback OK" if result.success else f"Playback FAILED: {result.error}")


if __name__ == "__main__":
    main()
