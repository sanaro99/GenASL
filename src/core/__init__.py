"""Shared core utilities — paths, typed settings, logging, ffmpeg discovery."""

from src.core.config import Settings, get_settings, reset_settings
from src.core.ffmpeg import find_ffmpeg, find_ffprobe
from src.core.logging import setup_logging
from src.core.paths import PROJECT_ROOT

__all__ = [
    "PROJECT_ROOT",
    "Settings",
    "get_settings",
    "reset_settings",
    "setup_logging",
    "find_ffmpeg",
    "find_ffprobe",
]
