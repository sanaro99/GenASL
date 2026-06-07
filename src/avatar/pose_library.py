"""Runtime loader for the WLASL per-gloss pose library (Phase 4 fallback).

The pose library is the *last-resort* tier in Phase 5's tiered
retrieval: when both the OpenASL phrase index and the ASL Citizen
lexical index miss above their thresholds, we stitch one WLASL clip
per gloss in ``AslPlanSegment.sign_sequence``. Each library entry is
keyframes of a single Deaf-signed isolated-sign clip, extracted by
``scripts/build_pose_library.py``.

Loading is lazy — instantiating :class:`PoseLibrary` touches no JSON;
only ``get()`` reads from disk.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import BaseModel

from src.core.paths import PROJECT_ROOT
from src.pipeline.models import MotionFrame, NmmFrame

logger = logging.getLogger(__name__)


class PoseLibraryEntry(BaseModel):
    gloss: str
    duration_ms: int
    fps: int = 30
    source_clip: str = ""
    keyframes: list[MotionFrame]
    nmm: list[NmmFrame] = []


class PoseLibrary:
    """File-backed pose library, keyed by uppercase gloss."""

    def __init__(self, root: Path | None = None) -> None:
        from src.core.config import get_settings
        s = get_settings()
        self.root = root or (PROJECT_ROOT / s.paths.pose_library)
        self._cache: dict[str, PoseLibraryEntry] = {}

    @property
    def glosses(self) -> set[str]:
        if not self.root.is_dir():
            return set()
        return {p.stem.upper() for p in self.root.glob("*.json")}

    def has(self, gloss: str) -> bool:
        path = self._path_for(gloss)
        return path is not None and path.is_file()

    def get(self, gloss: str) -> PoseLibraryEntry:
        gloss = gloss.upper()
        if gloss in self._cache:
            return self._cache[gloss]
        path = self._path_for(gloss)
        if path is None or not path.is_file():
            raise KeyError(f"Pose library has no entry for {gloss!r}")
        entry = PoseLibraryEntry.model_validate_json(path.read_text(encoding="utf-8"))
        self._cache[gloss] = entry
        return entry

    def _path_for(self, gloss: str) -> Path | None:
        if not gloss:
            return None
        return self.root / f"{gloss.upper()}.json"


__all__ = ["PoseLibrary", "PoseLibraryEntry"]
