"""Wrapper around the Piper offline TTS CLI.

Piper is invoked as a subprocess (CLAUDE.md §11:
`echo "..." | piper --model ... --output_file ...`). The engine and
voice model are never assumed to be installed — callers get a failed
`SynthesisResult` (missing binary, missing model, bad input, timeout)
rather than an exception, since a TTS outage must not crash the Flask
app or the announcement worker.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class SynthesisResult:
    success: bool
    output_path: Optional[str] = None
    voice_model: Optional[str] = None
    error: Optional[str] = None


class PiperEngine:
    def __init__(self, executable: str = "piper", model_path: str = "", timeout: float = 60.0) -> None:
        self._executable = executable
        self._model_path = model_path
        self._timeout = timeout

    def is_available(self) -> bool:
        return shutil.which(self._executable) is not None and Path(self._model_path).exists()

    def synthesize(self, text: str, output_path: str) -> SynthesisResult:
        if not text.strip():
            return SynthesisResult(success=False, error="Empty text")

        if shutil.which(self._executable) is None:
            return SynthesisResult(success=False, error=f"Piper executable not found: {self._executable}")

        if not Path(self._model_path).exists():
            return SynthesisResult(success=False, error=f"Voice model not found: {self._model_path}")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        try:
            process = subprocess.run(
                [self._executable, "--model", self._model_path, "--output_file", output_path],
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=self._timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return SynthesisResult(success=False, error="Piper synthesis timed out")
        except OSError as exc:
            return SynthesisResult(success=False, error=f"Failed to run piper: {exc}")

        if process.returncode != 0:
            stderr = process.stderr.decode("utf-8", errors="ignore")
            return SynthesisResult(success=False, error=f"Piper exited {process.returncode}: {stderr}")

        if not Path(output_path).exists():
            return SynthesisResult(success=False, error="Piper reported success but produced no output file")

        return SynthesisResult(success=True, output_path=output_path, voice_model=self._model_path)
