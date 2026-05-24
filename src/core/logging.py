"""Project-wide logging setup.

Replaces the dual handler block that used to live at module top of
``run_pipeline.py`` and run on import. Call :func:`setup_logging` once
from an entry point (CLI, API server).
"""

from __future__ import annotations

import logging
import os

from src.core.paths import LOGS_DIR

_LOG_FORMAT = "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"
_FILE_LOG_NAME = "pipeline_debug.log"
_initialised = False


def setup_logging() -> None:
    """Configure root logger with a console handler (INFO) + file handler (DEBUG).

    Idempotent — repeated calls are a no-op so tests, the CLI, and the API
    server can each call it without doubling handlers.
    """
    global _initialised
    if _initialised:
        return

    os.makedirs(LOGS_DIR, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(_LOG_FORMAT))
    root.addHandler(console)

    file_h = logging.FileHandler(LOGS_DIR / _FILE_LOG_NAME, mode="w", encoding="utf-8")
    file_h.setLevel(logging.DEBUG)
    file_h.setFormatter(logging.Formatter(_LOG_FORMAT))
    root.addHandler(file_h)

    logging.getLogger(__name__).info("Log file: %s", LOGS_DIR / _FILE_LOG_NAME)
    _initialised = True
