"""Abstract Stage with on-disk caching.

Each stage takes a typed Pydantic input, returns a typed Pydantic output,
and caches the output on disk keyed by a fingerprint. Re-running the
pipeline on an already-processed input is therefore a JSON read.
"""

from __future__ import annotations

import hashlib
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import ClassVar, Generic, TypeVar

from pydantic import BaseModel

from src.core.config import Settings
from src.core.paths import PROJECT_ROOT

logger = logging.getLogger(__name__)

InT = TypeVar("InT", bound=BaseModel)
OutT = TypeVar("OutT", bound=BaseModel)


def stable_hash(parts: list) -> str:
    """Deterministic short hex hash of an ordered list of stringifiable parts."""
    h = hashlib.sha256()
    for p in parts:
        h.update(str(p).encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()[:16]


class Stage(Generic[InT, OutT], ABC):
    """Base class for pipeline stages with per-stage disk cache."""

    name: ClassVar[str]
    output_model: ClassVar[type[BaseModel]]

    def __init__(self, settings: Settings, cache_root: Path | None = None) -> None:
        self.settings = settings
        root = cache_root or (PROJECT_ROOT / settings.paths.cache_dir)
        self.cache_dir = root / self.name
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def fingerprint(self, inp: InT) -> str:
        """Return a stable hash key over (input, relevant settings)."""

    @abstractmethod
    def process(self, inp: InT) -> OutT:
        """Run the stage. Called only when the cache misses."""

    def run(self, inp: InT, *, use_cache: bool = True) -> OutT:
        """Execute the stage, hitting the disk cache when possible."""
        key = self.fingerprint(inp)
        path = self.cache_dir / f"{key}.json"
        if use_cache and path.is_file():
            logger.info("Stage %s: cache HIT  key=%s", self.name, key)
            return self.output_model.model_validate_json(
                path.read_text(encoding="utf-8")
            )
        logger.info("Stage %s: cache MISS key=%s — running", self.name, key)
        out = self.process(inp)
        path.write_text(out.model_dump_json(indent=2), encoding="utf-8")
        return out
