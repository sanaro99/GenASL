"""Project-wide logging setup.

Two entry points:
  * :func:`setup_logging` — used by the CLI, the API server, and tests.
    Idempotent; writes to ``logs/pipeline_debug.log``.
  * :func:`setup_script_logging` — used by the long-running offline
    scripts under ``scripts/`` (corpus fetch, index build, pose extract).
    Each script gets its own timestamped log file so the user can watch
    them in real time and post-mortem later, without one script's logs
    clobbering another's.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

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


def setup_script_logging(
    script_name: str,
    *,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
) -> Path:
    """Configure a script's root logger with timestamped per-script log file.

    Always appends a fresh file handler (no idempotency guard) — each
    invocation of an offline script should produce a dedicated log so
    parallel or sequential runs don't collide.

    Returns the log file path so the script can print it for the user.
    """
    os.makedirs(LOGS_DIR, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    log_path = LOGS_DIR / f"{script_name}-{stamp}.log"

    root = logging.getLogger()
    root.setLevel(min(console_level, file_level))

    # Wipe any existing handlers so the per-script run is self-contained.
    for handler in list(root.handlers):
        root.removeHandler(handler)

    console = logging.StreamHandler()
    console.setLevel(console_level)
    console.setFormatter(logging.Formatter(_LOG_FORMAT))
    root.addHandler(console)

    file_h = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    file_h.setLevel(file_level)
    file_h.setFormatter(logging.Formatter(_LOG_FORMAT))
    root.addHandler(file_h)

    logging.getLogger(__name__).info(
        "Script %s logging to %s (console=%s, file=%s)",
        script_name, log_path,
        logging.getLevelName(console_level),
        logging.getLevelName(file_level),
    )
    return log_path
