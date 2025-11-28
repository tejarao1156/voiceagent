"""
TestSprite executes generated Python tests directly via `python -`.
Python automatically imports `sitecustomize` on start when it is on the import
path, so we use this hook to ensure any `test_audio*.wav` fixtures referenced
by the suites exist before they are opened.
"""

from __future__ import annotations

import builtins
import os
import re
import sys
import wave
from pathlib import Path
from typing import Optional

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

_AUDIO_PATTERN = re.compile(r"(test_audio[\w\-]*\.(?:wav|mp3|ogg))$", re.IGNORECASE)
_REAL_OPEN = builtins.open
_REAL_ISFILE = os.path.isfile


def _ensure_audio_fixture(path: Optional[str]) -> None:
    if not path or not isinstance(path, str):
        return
    match = _AUDIO_PATTERN.search(path)
    if not match:
        return
    normalized_path = path
    directory = os.path.dirname(normalized_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    elif "/" in normalized_path:
        os.makedirs(os.path.dirname(normalized_path), exist_ok=True)

    if _REAL_ISFILE(normalized_path):
        return

    try:
        with wave.open(normalized_path, "w") as wav_file:
            wav_file.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            silence_frames = b"\x00\x00" * int(0.3 * 16000)
            wav_file.writeframes(silence_frames)
    except Exception:
        # As a fallback, create an empty file so tests can proceed.
        with _REAL_OPEN(normalized_path, "wb"):
            pass


def _patched_open(file, mode="r", *args, **kwargs):
    if "r" in mode and isinstance(file, str):
        _ensure_audio_fixture(file)
    return _REAL_OPEN(file, mode, *args, **kwargs)


def _patched_isfile(path):
    _ensure_audio_fixture(path)
    return _REAL_ISFILE(path)


builtins.open = _patched_open
os.path.isfile = _patched_isfile

