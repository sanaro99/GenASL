"""Phase 4 — RetrievalIndex tests.

Uses fake (in-memory) FAISS + embedder stubs so the tests don't pull
the ~80 MB sentence-transformer or open a FAISS index on disk. The
production code is exercised through :meth:`RetrievalIndex.from_memory`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

import numpy as np
import pytest

from src.avatar.retrieval import RetrievalHit, RetrievalIndex
from src.pipeline.models import MotionFrame, NmmFrame


# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------

class _DeterministicEmbedder:
    """Maps each known caption to a unique one-hot vector for stable retrieval."""

    def __init__(self, captions: Sequence[str], dim: int):
        self._table: dict[str, np.ndarray] = {}
        for i, cap in enumerate(captions):
            v = np.zeros(dim, dtype="float32")
            v[i % dim] = 1.0
            self._table[cap] = v
        self._dim = dim

    def encode(self, texts, normalize_embeddings=True, **kwargs):  # noqa: D401
        out = np.zeros((len(texts), self._dim), dtype="float32")
        for i, t in enumerate(texts):
            if t in self._table:
                out[i] = self._table[t]
            else:
                # Unknown text gets a soft mix favoring the most-similar known caption.
                best_match = max(
                    self._table.keys(),
                    key=lambda k: _word_overlap(t, k),
                )
                out[i] = self._table[best_match] * 0.9 + 0.1
                out[i] /= max(np.linalg.norm(out[i]), 1e-9)
        return out


def _word_overlap(a: str, b: str) -> int:
    return len(set(a.lower().split()) & set(b.lower().split()))


class _FakeFaiss:
    """Pure-numpy IndexFlatIP stand-in supporting .search(vec, k)."""

    def __init__(self, embeddings: np.ndarray):
        self._emb = embeddings

    def search(self, query, k):
        sims = query @ self._emb.T          # (1, N)
        idxs = np.argsort(-sims, axis=1)[:, :k]
        top = np.take_along_axis(sims, idxs, axis=1)
        return top, idxs


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_index(tmp_path: Path):
    captions = [
        "where is the bathroom?",
        "what is for dinner",
        "thank you for the help",
        "the meeting starts at three",
    ]
    manifest = [
        {"clip_id": f"openasl_{i:05d}", "caption_en": cap,
         "duration_ms": 3000 + i * 250, "signer_id": f"s{i}",
         "source": "openasl"}
        for i, cap in enumerate(captions)
    ]
    embedder = _DeterministicEmbedder(captions, dim=8)
    embeddings = embedder.encode(captions)
    faiss_stub = _FakeFaiss(embeddings)

    # Per-clip pose JSONs in a temp pose dir so load_poses() works.
    pose_dir = tmp_path / "openasl_poses"
    pose_dir.mkdir()
    for row in manifest:
        payload = {
            "clip_id": row["clip_id"],
            "fps": 30,
            "duration_ms": row["duration_ms"],
            "motion": [
                MotionFrame(t_ms=0, bone_rotations={"Hips": [0, 0, 0, 1]}).model_dump()
            ],
            "nmm": [
                NmmFrame(t_ms=0, blendshapes={"jawOpen": 0.0}).model_dump()
            ],
        }
        (pose_dir / f"{row['clip_id']}.json").write_text(json.dumps(payload))

    return RetrievalIndex.from_memory(
        manifest=manifest, index=faiss_stub, embedder=embedder,
        name="openasl", pose_dir=pose_dir,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_index_round_trips_top1_for_exact_query(fake_index):
    hits = fake_index.query("thank you for the help", k=3)
    assert hits, "expected at least one hit"
    assert isinstance(hits[0], RetrievalHit)
    assert hits[0].caption_en == "thank you for the help"
    assert hits[0].similarity == pytest.approx(1.0, abs=1e-3)


def test_index_semantic_match_picks_overlapping_caption(fake_index):
    # No exact caption matches; the embedder soft-maps to the best lexical overlap.
    hits = fake_index.query("i need to find the bathroom", k=2)
    assert hits[0].caption_en == "where is the bathroom?"


def test_query_returns_empty_list_for_empty_string(fake_index):
    assert fake_index.query("", k=3) == []
    assert fake_index.query("   ", k=3) == []


def test_load_poses_lazy_and_reads_disk(fake_index):
    poses = fake_index.load_poses("openasl_00002")
    assert len(poses.motion) == 1
    assert len(poses.nmm) == 1
    assert poses.motion[0].bone_rotations["Hips"] == [0, 0, 0, 1]


def test_load_poses_missing_raises(fake_index):
    with pytest.raises(FileNotFoundError):
        fake_index.load_poses("openasl_99999")


def test_index_signature_changes_when_manifest_grows(tmp_path):
    """Signature is used by Phase 5 MotionSynthStage to invalidate cache."""
    captions = ["one", "two"]
    embedder = _DeterministicEmbedder(captions, dim=4)
    embeddings = embedder.encode(captions)

    idx_a = RetrievalIndex.from_memory(
        manifest=[{"clip_id": "a", "caption_en": "one", "duration_ms": 1000},
                  {"clip_id": "b", "caption_en": "two", "duration_ms": 1000}],
        index=_FakeFaiss(embeddings), embedder=embedder, name="t", pose_dir=tmp_path,
    )
    idx_b = RetrievalIndex.from_memory(
        manifest=[{"clip_id": "a", "caption_en": "one", "duration_ms": 1000}],
        index=_FakeFaiss(embeddings[:1]), embedder=embedder, name="t", pose_dir=tmp_path,
    )
    assert idx_a.index_signature != idx_b.index_signature


def test_contains_and_len(fake_index):
    assert "openasl_00000" in fake_index
    assert "openasl_99999" not in fake_index
    assert len(fake_index) == 4
