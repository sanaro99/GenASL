"""Canonical filesystem paths for the project.

Single source of truth — every module that needs a project-relative path
should import from here rather than re-deriving ``Path(__file__).parents[N]``.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]

SRC_DIR: Path = PROJECT_ROOT / "src"
ASSETS_DIR: Path = PROJECT_ROOT / "assets"
DATA_DIR: Path = PROJECT_ROOT / "data"
LOGS_DIR: Path = PROJECT_ROOT / "logs"
TRANSCRIPTS_DIR: Path = PROJECT_ROOT / "transcripts"

CHAINED_CLIPS_DIR: Path = ASSETS_DIR / "chained"
WORDS_DIR: Path = ASSETS_DIR / "words"
WORD_MANIFEST: Path = ASSETS_DIR / "word_manifest.json"

CACHE_DIR: Path = DATA_DIR / "cache"

CONFIG_YAML: Path = PROJECT_ROOT / "config.yaml"
COOKIES_TXT: Path = PROJECT_ROOT / "cookies.txt"
