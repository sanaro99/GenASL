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

# Phase 4 corpus root + helpers. Concrete primary/secondary corpus
# names live under settings.retrieval; these helpers join consistently.
CORPUS_ROOT: Path = ASSETS_DIR / "corpus"


def corpus_clip_dir(name: str) -> Path:
    """`assets/corpus/<name>/` — video bytes (gitignored)."""
    return CORPUS_ROOT / name


def corpus_pose_dir(name: str) -> Path:
    """`assets/corpus/<name>_poses/` — per-clip pose JSON (gitignored)."""
    return CORPUS_ROOT / f"{name}_poses"


def corpus_manifest_path(name: str) -> Path:
    """`assets/corpus/<name>_manifest.json` — tracked."""
    return CORPUS_ROOT / f"{name}_manifest.json"


def corpus_index_path(name: str) -> Path:
    """`assets/corpus/<name>.faiss` — tracked (tens of MB)."""
    return CORPUS_ROOT / f"{name}.faiss"


def corpus_embeddings_path(name: str) -> Path:
    """`assets/corpus/<name>_embeddings.npy` — gitignored convenience."""
    return CORPUS_ROOT / f"{name}_embeddings.npy"

CONFIG_YAML: Path = PROJECT_ROOT / "config.yaml"
COOKIES_TXT: Path = PROJECT_ROOT / "cookies.txt"
