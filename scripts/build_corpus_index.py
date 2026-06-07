"""Build the FAISS caption index + per-clip pose JSON for a corpus (Phase 4).

Reads ``assets/corpus/<name>_manifest.json`` (produced by
``scripts/fetch_openasl.py``) and writes:

  * ``assets/corpus/<name>.faiss``                 — FAISS index (tracked)
  * ``assets/corpus/<name>_embeddings.npy``        — raw embeddings (gitignored)
  * ``assets/corpus/<name>_poses/<clip_id>.json``  — per-clip pose stream

The embeddings step is fast (~minutes on GPU, ~tens-of-minutes on CPU);
the pose extraction step is the long one — plan for ~real-time per
clip on CPU. Use ``--skip-poses`` for an embedding-only rebuild after
tweaking the embedding model, or ``--skip-index`` to re-extract poses
only.

Logging
-------
Each invocation writes ``logs/build_corpus_index-<YYYYMMDD-HHMMSS>.log``.
Pass ``--log-level DEBUG`` for per-frame extraction detail.

Usage
-----
    # Smoke test on the first 50 clips
    python -m scripts.build_corpus_index --limit 50

    # Full build
    python -m scripts.build_corpus_index

    # Re-embed only (e.g. after changing retrieval.embedding_model)
    python -m scripts.build_corpus_index --skip-poses

    # Re-extract poses only (e.g. after fixing the retargeter)
    python -m scripts.build_corpus_index --skip-index
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from src.core.config import get_settings
from src.core.logging import setup_script_logging
from src.core.paths import (
    PROJECT_ROOT,
    corpus_embeddings_path,
    corpus_index_path,
    corpus_manifest_path,
    corpus_pose_dir,
)

logger = logging.getLogger("build_corpus_index")


# ---------------------------------------------------------------------------
# Manifest loading
# ---------------------------------------------------------------------------

def _load_manifest(name: str) -> list[dict]:
    path = corpus_manifest_path(name)
    if not path.is_file():
        raise FileNotFoundError(
            f"Manifest {path} not found. Run scripts/fetch_openasl.py first.")
    rows = json.loads(path.read_text(encoding="utf-8"))
    logger.info("Loaded %d rows from %s", len(rows), path)
    return rows


# ---------------------------------------------------------------------------
# Embedding + FAISS index
# ---------------------------------------------------------------------------

def build_embeddings_and_index(rows: list[dict], name: str) -> None:
    from sentence_transformers import SentenceTransformer  # type: ignore
    import faiss  # type: ignore
    import numpy as np  # type: ignore

    settings = get_settings().retrieval
    captions = [r.get("caption_en", "") for r in rows]
    logger.info("Embedding %d captions with %s (batch=128) …",
                len(captions), settings.embedding_model)
    t0 = time.monotonic()
    model = SentenceTransformer(settings.embedding_model)
    embeddings = model.encode(
        captions,
        batch_size=128,
        show_progress_bar=True,
        normalize_embeddings=True,        # cosine sim ↔ inner product
        convert_to_numpy=True,
    ).astype("float32")
    logger.info("Embeddings shape=%s in %.1fs", embeddings.shape,
                time.monotonic() - t0)

    np.save(corpus_embeddings_path(name), embeddings)
    logger.info("Wrote raw embeddings to %s", corpus_embeddings_path(name))

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    faiss.write_index(index, str(corpus_index_path(name)))
    logger.info("FAISS index (dim=%d, n=%d) → %s",
                dim, index.ntotal, corpus_index_path(name))


# ---------------------------------------------------------------------------
# Pose extraction — one process per clip so mediapipe state is isolated
# ---------------------------------------------------------------------------

def _pose_worker(row: dict, target_fps: int, out_dir: str) -> tuple[str, bool, str]:
    """Run in a child process. Returns (clip_id, ok, message)."""
    import logging as _logging
    # Each subprocess sets up its own stream handler so messages reach
    # the parent's combined log via redirection.
    _logging.basicConfig(
        level=_logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    )
    try:
        from src.avatar.pose_extractor import extract_pose_stream
        from src.core.paths import PROJECT_ROOT as _ROOT

        clip_id = row["clip_id"]
        out_path = Path(out_dir) / f"{clip_id}.json"
        if out_path.is_file() and out_path.stat().st_size > 0:
            return clip_id, True, "skip-existing"

        mp4_rel = row["mp4_path"]
        mp4_path = (_ROOT / mp4_rel).resolve()
        if not mp4_path.is_file():
            return clip_id, False, f"mp4 not found: {mp4_path}"

        stream = extract_pose_stream(mp4_path, target_fps=target_fps)
        payload = {
            "clip_id": clip_id,
            "fps": stream.fps,
            "duration_ms": stream.duration_ms,
            "motion": [m.model_dump() for m in stream.motion],
            "nmm": [n.model_dump() for n in stream.nmm],
        }
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload), encoding="utf-8")
        return clip_id, True, f"frames={len(stream.motion)}"
    except Exception as exc:
        return row.get("clip_id", "?"), False, f"{type(exc).__name__}: {exc}"


def extract_all_poses(rows: list[dict], name: str, *,
                      workers: int, target_fps: int) -> None:
    out_dir = corpus_pose_dir(name)
    out_dir.mkdir(parents=True, exist_ok=True)
    logger.info(
        "Extracting poses for %d clips at %d fps → %s (workers=%d)",
        len(rows), target_fps, out_dir, workers,
    )

    t_start = time.monotonic()
    succeeded = 0
    failed = 0
    skipped = 0

    if workers <= 1:
        # In-process — easier to debug + avoids the per-call subprocess
        # overhead on small runs.
        for i, row in enumerate(rows, 1):
            clip_id, ok, msg = _pose_worker(row, target_fps, str(out_dir))
            _record(clip_id, ok, msg)
            if ok and msg == "skip-existing":
                skipped += 1
            elif ok:
                succeeded += 1
            else:
                failed += 1
            if i % 25 == 0:
                _emit_progress(i, len(rows), t_start, succeeded, failed, skipped)
    else:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(_pose_worker, r, target_fps, str(out_dir)): r
                    for r in rows}
            done = 0
            for fut in as_completed(futs):
                clip_id, ok, msg = fut.result()
                _record(clip_id, ok, msg)
                done += 1
                if ok and msg == "skip-existing":
                    skipped += 1
                elif ok:
                    succeeded += 1
                else:
                    failed += 1
                if done % 25 == 0:
                    _emit_progress(done, len(rows), t_start,
                                   succeeded, failed, skipped)

    elapsed = time.monotonic() - t_start
    logger.info(
        "Pose extraction done. succeeded=%d failed=%d skipped=%d "
        "elapsed=%.1fs (%.1f clips/s)",
        succeeded, failed, skipped, elapsed,
        len(rows) / max(elapsed, 1e-6),
    )


def _record(clip_id: str, ok: bool, msg: str) -> None:
    level = logging.DEBUG if ok else logging.ERROR
    logger.log(level, "pose %s — %s — %s", clip_id, "ok" if ok else "FAIL", msg)


def _emit_progress(done: int, total: int, t_start: float,
                   ok: int, fail: int, skip: int) -> None:
    rate = done / max(time.monotonic() - t_start, 1e-6)
    eta_s = (total - done) / max(rate, 1e-6)
    logger.info(
        "  Progress: %d/%d (ok=%d fail=%d skip=%d) %.2f clips/s ETA %.0fs",
        done, total, ok, fail, skip, rate, eta_s,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build the FAISS index + per-clip poses for the OpenASL corpus.")
    p.add_argument("--name", default=None,
                   help="Corpus name (default: settings.retrieval.primary_corpus, "
                        "typically 'openasl').")
    p.add_argument("--limit", type=int, default=0,
                   help="Process only the first N rows (0 = all).")
    p.add_argument("--skip-poses", action="store_true",
                   help="Build embeddings + index only; skip pose extraction.")
    p.add_argument("--skip-index", action="store_true",
                   help="Extract poses only; skip embeddings + FAISS index.")
    p.add_argument("--workers", type=int, default=2,
                   help="Pose-extraction worker processes (mediapipe is "
                        "single-threaded internally).")
    p.add_argument("--target-fps", type=int, default=None,
                   help="Pose sampling rate (default: settings.avatar.frame_rate).")
    p.add_argument("--log-level", default="INFO",
                   choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    log_path = setup_script_logging(
        "build_corpus_index",
        console_level=getattr(logging, args.log_level),
        file_level=logging.DEBUG,
    )
    logger.info("build_corpus_index starting — log file: %s", log_path)

    settings = get_settings()
    name = args.name or settings.retrieval.primary_corpus
    target_fps = args.target_fps or settings.avatar.frame_rate

    rows = _load_manifest(name)
    if args.limit > 0:
        rows = rows[: args.limit]
        logger.info("Limited to first %d rows", args.limit)

    if not args.skip_index:
        build_embeddings_and_index(rows, name)
    else:
        logger.info("--skip-index set; not rebuilding embeddings/FAISS")

    if not args.skip_poses:
        extract_all_poses(rows, name,
                          workers=args.workers, target_fps=target_fps)
    else:
        logger.info("--skip-poses set; not extracting poses")

    logger.info("Done. log file: %s", log_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
