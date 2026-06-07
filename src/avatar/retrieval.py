"""Phrase-level retrieval over a Deaf-signed corpus (Phase 4).

Loads a FAISS index of sentence-transformer caption embeddings and the
matching corpus manifest. Provides:

* :meth:`RetrievalIndex.query` — embed an English query and return the
  top-k semantically-similar clips, each as a :class:`RetrievalHit`
  with cosine similarity in [0, 1].
* :meth:`RetrievalIndex.load_poses` — read the per-clip VRM-rig
  ``MotionFrame`` stream that ``build_corpus_index.py`` produced.

Heavy deps (``faiss``, ``sentence_transformers``) are imported lazily
so the test suite can stub the index in-memory.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from pydantic import BaseModel

from src.core.config import RetrievalSettings, get_settings
from src.core.paths import (
    corpus_index_path,
    corpus_manifest_path,
    corpus_pose_dir,
)
from src.pipeline.models import MotionFrame, NmmFrame

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public data shapes
# ---------------------------------------------------------------------------

class RetrievalHit(BaseModel):
    clip_id: str
    similarity: float                # cosine, normalised into [0, 1]
    caption_en: str
    duration_ms: int
    signer_id: str | None = None
    source: str = ""                 # corpus name, e.g. "openasl"


@dataclass
class _LoadedPoses:
    motion: list[MotionFrame]
    nmm: list[NmmFrame]


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------

class RetrievalIndex:
    """Lazy loader + query API for one corpus.

    Construct with ``RetrievalIndex(name="openasl")``. The FAISS index
    and embedding model are loaded on the first :meth:`query` call —
    importing this module is free.
    """

    def __init__(
        self,
        name: str | None = None,
        settings: RetrievalSettings | None = None,
    ) -> None:
        self.settings = settings or get_settings().retrieval
        self.name = name or self.settings.primary_corpus

        self.manifest_path = corpus_manifest_path(self.name)
        self.index_path = corpus_index_path(self.name)
        self.pose_dir = corpus_pose_dir(self.name)

        self._index = None
        self._embedder = None
        self._manifest: list[dict] | None = None
        self._clip_id_to_row: dict[str, dict] | None = None

    # ------------------------------------------------------------------
    # Inspection helpers (used by Phase 5 fingerprint + tests)
    # ------------------------------------------------------------------
    @property
    def index_signature(self) -> str:
        """Cheap stable hash of the index file's mtime + manifest length."""
        manifest_n = len(self._load_manifest())
        try:
            mtime = int(self.index_path.stat().st_mtime)
        except FileNotFoundError:
            mtime = 0
        return f"{self.name}:{manifest_n}:{mtime}"

    def __contains__(self, clip_id: str) -> bool:
        return clip_id in self._clip_id_index()

    def __len__(self) -> int:
        return len(self._load_manifest())

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------
    def query(self, text: str, k: int = 5) -> list[RetrievalHit]:
        text = (text or "").strip()
        if not text:
            return []
        index = self._load_index()
        embedder = self._load_embedder()
        manifest = self._load_manifest()

        vec = embedder.encode([text], normalize_embeddings=True)
        # FAISS inner product on normalized vectors = cosine.
        sims, idxs = index.search(vec, k)
        hits: list[RetrievalHit] = []
        for sim, row_idx in zip(sims[0].tolist(), idxs[0].tolist()):
            if row_idx < 0 or row_idx >= len(manifest):
                continue
            row = manifest[row_idx]
            # Inner-product on normalized vectors is already in [-1, 1];
            # clamp to [0, 1] so callers can compare to a threshold easily.
            cosine = max(0.0, min(1.0, float(sim)))
            hits.append(RetrievalHit(
                clip_id=row["clip_id"],
                similarity=cosine,
                caption_en=row.get("caption_en", ""),
                duration_ms=int(row.get("duration_ms", 0)),
                signer_id=row.get("signer_id"),
                source=row.get("source", self.name),
            ))
        return hits

    # ------------------------------------------------------------------
    # Pose loading
    # ------------------------------------------------------------------
    def load_poses(self, clip_id: str) -> _LoadedPoses:
        path = self.pose_dir / f"{clip_id}.json"
        if not path.is_file():
            raise FileNotFoundError(
                f"Pose file for clip {clip_id!r} not found at {path}. "
                "Run scripts/build_corpus_index.py to extract poses."
            )
        data = json.loads(path.read_text(encoding="utf-8"))
        motion = [MotionFrame.model_validate(d) for d in data.get("motion", [])]
        nmm = [NmmFrame.model_validate(d) for d in data.get("nmm", [])]
        return _LoadedPoses(motion=motion, nmm=nmm)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _load_index(self):
        if self._index is None:
            import faiss  # type: ignore
            if not self.index_path.is_file():
                raise FileNotFoundError(
                    f"FAISS index not found at {self.index_path}. "
                    "Run scripts/build_corpus_index.py first."
                )
            logger.info("Loading FAISS index %s", self.index_path)
            self._index = faiss.read_index(str(self.index_path))
        return self._index

    def _load_embedder(self):
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer  # type: ignore
            logger.info("Loading embedder %s", self.settings.embedding_model)
            self._embedder = SentenceTransformer(self.settings.embedding_model)
        return self._embedder

    def _load_manifest(self) -> list[dict]:
        if self._manifest is None:
            if not self.manifest_path.is_file():
                raise FileNotFoundError(
                    f"Corpus manifest not found at {self.manifest_path}. "
                    "Run scripts/fetch_openasl.py first."
                )
            logger.info("Loading manifest %s", self.manifest_path)
            raw = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            self._manifest = list(raw)
        return self._manifest

    def _clip_id_index(self) -> dict[str, dict]:
        if self._clip_id_to_row is None:
            self._clip_id_to_row = {row["clip_id"]: row
                                    for row in self._load_manifest()}
        return self._clip_id_to_row

    # ------------------------------------------------------------------
    # Test seam — used by tests/test_retrieval.py to bypass FAISS load
    # ------------------------------------------------------------------
    @classmethod
    def from_memory(
        cls,
        manifest: Sequence[dict],
        index,
        embedder,
        *,
        name: str = "test",
        pose_dir: Path | None = None,
    ) -> "RetrievalIndex":
        """Construct an instance from in-memory state (no file I/O)."""
        obj = cls.__new__(cls)
        obj.settings = get_settings().retrieval
        obj.name = name
        obj.manifest_path = corpus_manifest_path(name)
        obj.index_path = corpus_index_path(name)
        obj.pose_dir = pose_dir or corpus_pose_dir(name)
        obj._index = index
        obj._embedder = embedder
        obj._manifest = list(manifest)
        obj._clip_id_to_row = {row["clip_id"]: row for row in obj._manifest}
        return obj


__all__ = ["RetrievalIndex", "RetrievalHit"]
