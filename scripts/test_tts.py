"""Manual test: synthesize a line of Thai text with Piper and report
whether it worked. Run on the target Raspberry Pi -- Piper and the
voice model are not installed in this repo (CLAUDE.md section 11).

Usage: python scripts/test_tts.py ["text to speak"]
"""

from __future__ import annotations

import sys

from config import Config
from modules.tts.audio_converter import inspect_wav
from modules.tts.piper_engine import PiperEngine


def main() -> None:
    text = sys.argv[1] if len(sys.argv) > 1 else "ทดสอบระบบเสียงประกาศ"
    engine = PiperEngine(executable=Config.PIPER_EXECUTABLE, model_path=Config.PIPER_MODEL)
    output_path = "static/audio/tts_test.wav"

    result = engine.synthesize(text, output_path)
    if not result.success:
        print(f"FAILED: {result.error}")
        sys.exit(1)

    info = inspect_wav(result.output_path)
    print(f"OK: wrote {result.output_path} (valid={info.valid}, duration={info.duration_seconds}s)")


if __name__ == "__main__":
    main()
