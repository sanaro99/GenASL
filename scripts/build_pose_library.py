"""Build the WLASL per-gloss pose library -- Phase 5 fallback tier.

Walks ``assets/word_manifest.json``, picks the best clip per gloss
(honoring ``preferred_signer_ids``), runs Mediapipe Holistic via
``src.avatar.pose_extractor.extract_pose_stream``, and writes a
:class:`PoseLibraryEntry`-shaped JSON to
``assets/pose_library/<GLOSS>.json``.

Defaults to the **top 500 glosses** per the corpus-retrieval pivot --
the full 2 000-entry build is no longer the primary path. Use
``--all`` to build everything (approximately several hours on CPU).

Logging
-------
Each invocation writes ``logs/build_pose_library-<YYYYMMDD-HHMMSS>.log``.

Usage
-----
    # Top-500 by manifest order (the fallback subset we ship by default)
    python -m scripts.build_pose_library

    # Single gloss for debugging
    python -m scripts.build_pose_library --gloss HELLO

    # Full build
    python -m scripts.build_pose_library --all
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from src.avatar.pose_extractor import extract_pose_stream
from src.avatar.pose_library import PoseLibraryEntry
from src.core.config import get_settings
from src.core.logging import setup_script_logging
from src.core.paths import PROJECT_ROOT, WORD_MANIFEST

logger = logging.getLogger("build_pose_library")


def _select_words(words: list[dict],
                  *,
                  preferred_signer_ids: list[int],
                  glosses: list[str] | None,
                  limit: int | None) -> list[dict]:
    """Pick one row per unique gloss, preferring the configured signers."""
    by_gloss: dict[str, dict] = {}
    for w in words:
        if w.get("qa_status") not in (None, "approved"):
            continue
        g = (w.get("gloss") or "").strip().upper()
        if not g:
            continue
        if glosses and g not in glosses:
            continue
        existing = by_gloss.get(g)
        # Prefer entries whose signer_id is in the preferred list.
        if existing is None:
            by_gloss[g] = w
            continue
        existing_preferred = existing.get("signer_id") in preferred_signer_ids
        candidate_preferred = w.get("signer_id") in preferred_signer_ids
        if candidate_preferred and not existing_preferred:
            by_gloss[g] = w
    out = sorted(by_gloss.values(), key=lambda w: w["gloss"].upper())
    if limit and limit > 0:
        out = out[: limit]
    return out


def _build_one(row: dict, out_dir: Path, target_fps: int, *,
               force: bool) -> tuple[str, bool, str]:
    gloss = row["gloss"].upper()
    out_path = out_dir / f"{gloss}.json"
    if out_path.is_file() and not force:
        return gloss, True, "skip-existing"
    clip_path = (PROJECT_ROOT / row["file_path"]).resolve()
    if not clip_path.is_file():
        return gloss, False, f"clip missing: {clip_path}"
    try:
        stream = extract_pose_stream(clip_path, target_fps=target_fps)
    except Exception as exc:
        return gloss, False, f"{type(exc).__name__}: {exc}"
    if not stream.motion:
        return gloss, False, "extractor returned 0 frames"
    entry = PoseLibraryEntry(
        gloss=gloss,
        duration_ms=stream.duration_ms,
        fps=stream.fps,
        source_clip=row.get("file_path", ""),
        keyframes=stream.motion,
        nmm=stream.nmm,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(entry.model_dump_json(), encoding="utf-8")
    return gloss, True, f"frames={len(stream.motion)}"


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--limit", type=int, default=500,
                   help="Build only the first N glosses (default 500; "
                        "use 0 for all).")
    p.add_argument("--all", action="store_true",
                   help="Alias for --limit 0 (build the whole library).")
    p.add_argument("--gloss", action="append", default=[],
                   help="Build only specific glosses (repeatable).")
    p.add_argument("--force", action="store_true",
                   help="Re-extract even when the JSON already exists.")
    p.add_argument("--target-fps", type=int, default=None,
                   help="Pose sampling rate (default: settings.avatar.frame_rate).")
    p.add_argument("--log-level", default="INFO",
                   choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    log_path = setup_script_logging(
        "build_pose_library",
        console_level=getattr(logging, args.log_level),
    )
    logger.info("build_pose_library starting — log file: %s", log_path)

    settings = get_settings()
    out_dir = PROJECT_ROOT / settings.paths.pose_library
    target_fps = args.target_fps or settings.avatar.frame_rate

    manifest = json.loads(WORD_MANIFEST.read_text(encoding="utf-8"))
    words = manifest.get("words", [])
    preferred = manifest.get("preferred_signer_ids", [])
    logger.info("Manifest: %d words, preferred signers=%s",
                len(words), preferred)

    glosses = [g.upper() for g in args.gloss] if args.gloss else None
    limit = 0 if args.all else args.limit
    rows = _select_words(
        words, preferred_signer_ids=preferred,
        glosses=glosses, limit=limit if limit > 0 else None,
    )
    logger.info("Building %d glosses → %s", len(rows), out_dir)

    succeeded = failed = skipped = 0
    t0 = time.monotonic()
    for i, row in enumerate(rows, 1):
        gloss, ok, msg = _build_one(row, out_dir, target_fps, force=args.force)
        if ok and msg == "skip-existing":
            skipped += 1
            logger.debug("[%d/%d] %s — skip (already on disk)", i, len(rows), gloss)
        elif ok:
            succeeded += 1
            logger.info("[%d/%d] %s — %s", i, len(rows), gloss, msg)
        else:
            failed += 1
            logger.error("[%d/%d] %s — FAIL — %s", i, len(rows), gloss, msg)
        if i % 25 == 0:
            rate = i / max(time.monotonic() - t0, 1e-6)
            logger.info(
                "  Progress: %d/%d (ok=%d fail=%d skip=%d) %.2f clips/s",
                i, len(rows), succeeded, failed, skipped, rate,
            )

    elapsed = time.monotonic() - t0
    logger.info(
        "Done. succeeded=%d failed=%d skipped=%d elapsed=%.1fs out=%s",
        succeeded, failed, skipped, elapsed, out_dir,
    )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
