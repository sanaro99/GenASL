"""FFmpeg / ffprobe binary discovery — single source of truth.

Replaces the duplicated ``_find_ffmpeg`` / ``_find_ffprobe`` helpers in
``src/gloss/chainer.py`` and ``src/compositor/compositor.py``.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

_WINGET_BIN_REL = (
    r"Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\ffmpeg-8.0.1-full_build\bin"
)


def _winget_bin(name: str) -> Path:
    local_app = Path(os.environ.get("LOCALAPPDATA", ""))
    return local_app / _WINGET_BIN_REL / f"{name}.exe"


def _find_binary(name: str) -> str:
    winget = _winget_bin(name)
    if winget.is_file():
        return str(winget)
    system = shutil.which(name)
    if system:
        return system
    raise FileNotFoundError(
        f"{name} not found. Install via 'winget install Gyan.FFmpeg' or add to PATH."
    )


def find_ffmpeg() -> str:
    """Return the absolute path to the ``ffmpeg`` binary."""
    return _find_binary("ffmpeg")


def find_ffprobe() -> str:
    """Return the absolute path to the ``ffprobe`` binary."""
    return _find_binary("ffprobe")
