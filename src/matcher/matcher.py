"""Semantic matcher — queries a FAISS index to map transcript segments to ASL assets.

On initialisation the matcher loads:
* the FAISS ``IndexFlatIP`` index,
* the companion ``index_metadata.json`` (position → sentence_id), and
* the sentence-transformer model

all from the paths / model name declared in ``config.yaml``.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List

import faiss
import numpy as np
import yaml
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_config() -> dict:
    cfg_path = _PROJECT_ROOT / "config.yaml"
    with open(cfg_path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


class Matcher:
    """Semantic matcher backed by FAISS and sentence-transformers."""

    def __init__(
        self,
        index: faiss.Index | None = None,
        metadata: Dict[str, str] | None = None,
        model: SentenceTransformer | None = None,
        confidence_threshold: float | None = None,
        top_k: int | None = None,
    ) -> None:
        cfg = _load_config()

        self._threshold = confidence_threshold if confidence_threshold is not None else cfg["matcher"]["confidence_threshold"]
        self._top_k = top_k if top_k is not None else cfg["matcher"]["top_k"]

        if index is not None:
            self._index = index
        else:
            index_path = _PROJECT_ROOT / cfg["paths"]["faiss_index"]
            self._index = faiss.read_index(str(index_path))

        if metadata is not None:
            self._metadata = metadata
        else:
            meta_path = _PROJECT_ROOT / cfg["paths"]["index_metadata"]
            with open(meta_path, "r", encoding="utf-8") as fh:
                self._metadata = json.load(fh)

        if model is not None:
            self._model = model
        else:
            self._model = SentenceTransformer(cfg["matcher"]["model_name"])

        # Build the allowlist of valid sentence_ids from metadata values
        self._valid_ids: set[str] = set(self._metadata.values())
        logger.info(
            "Matcher initialised: model=%s  threshold=%.2f  top_k=%d  "
            "index_size=%d  unique_sentence_ids=%d",
            cfg["matcher"]["model_name"],
            self._threshold,
            self._top_k,
            self._index.ntotal,
            len(self._valid_ids),
        )

    # -----------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------

    def match(self, segment: dict) -> dict:
        """Add ``action``, ``sentence_id``, and ``score`` fields to *segment*.

        Responsible-AI gate: even if the score exceeds the threshold, if the
        resolved ``sentence_id`` is **not** present in the metadata allowlist
        the segment is forced to ``CAPTIONS``.
        """
        text = segment["text"]

        # Encode and L2-normalise
        vec = self._model.encode([text], convert_to_numpy=True)
        faiss.normalize_L2(vec)

        # Query FAISS (inner-product ≈ cosine similarity after L2 norm)
        scores, indices = self._index.search(vec, self._top_k)
        best_score = float(scores[0][0])
        best_idx = int(indices[0][0])

        # Resolve sentence_id via metadata
        candidate_id = self._metadata.get(str(best_idx))

        # ── Responsible-AI gate ──────────────────────────────────────
        if best_score >= self._threshold and candidate_id in self._valid_ids:
            action = "ASL"
            sentence_id = candidate_id
        else:
            action = "CAPTIONS"
            sentence_id = None
            reason = (
                "below threshold"
                if best_score < self._threshold
                else "sentence_id not in allowlist"
            )
            logger.warning(
                "CAPTIONS fallback (%s): text=%r score=%.4f candidate=%s",
                reason,
                text,
                best_score,
                candidate_id,
            )

        result = dict(segment)
        result["action"] = action
        result["sentence_id"] = sentence_id
        result["score"] = round(best_score, 4)

        logger.info(
            "  %s  action=%-8s  score=%.4f  sentence_id=%-6s  text=%r",
            segment.get("segment_id", "?"),
            action,
            best_score,
            sentence_id or "—",
            text[:80],
        )
        return result

    def match_all(self, segments: List[dict]) -> List[dict]:
        """Run :meth:`match` on every segment and return the full list."""
        logger.info("Matching %d segments against FAISS index …", len(segments))
        results = [self.match(seg) for seg in segments]
        asl_count = sum(1 for r in results if r["action"] == "ASL")
        cap_count = len(results) - asl_count
        logger.info(
            "Matching complete: %d ASL, %d CAPTIONS out of %d total",
            asl_count, cap_count, len(results),
        )
        return results
