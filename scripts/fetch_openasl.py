"""Fetch the OpenASL phrase-level Deaf-signing corpus (Phase 4).

OpenASL distributes (YouTube ID, start, end, English caption) tuples
rather than raw video bytes (for copyright reasons). This script:

  1. Reads a *source* manifest produced by the upstream OpenASL release
     (TSV with columns: clip_id, youtube_id, start_seconds, end_seconds,
     caption_en, signer_id).  Pass it via ``--source PATH`` or
     ``--source URL``.
  2. For each row, downloads the source YouTube video once (cached
     under ``assets/corpus/openasl/_sources/<youtube_id>.mp4``).
  3. Trims [start, end] via ffmpeg to
     ``assets/corpus/openasl/<clip_id>.mp4``.
  4. Probes the trimmed clip for actual duration and appends an entry
     to ``assets/corpus/openasl_manifest.json``.

The output manifest is the input to ``scripts/build_corpus_index.py``.

Logging
-------
Every invocation writes a timestamped log at
``logs/fetch_openasl-<YYYYMMDD-HHMMSS>.log``. Pass ``--log-level DEBUG``
for per-frame detail. The path is printed at startup and at end so you
can ``tail -F`` it during long runs.

Usage
-----
    # Smoke test: pull 100 clips from a local source TSV
    python -m scripts.fetch_openasl --source path/to/openasl.tsv --limit 100

    # Full pull, 4 parallel workers, resume previous run
    python -m scripts.fetch_openasl --source path/to/openasl.tsv \
        --workers 4 --resume
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import logging
import shutil
import subprocess
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from src.audio.source_video import download_source_video
from src.core.config import get_settings
from src.core.ffmpeg import find_ffmpeg, find_ffprobe
from src.core.logging import setup_script_logging
from src.core.paths import (
    PROJECT_ROOT,
    corpus_clip_dir,
    corpus_manifest_path,
)

logger = logging.getLogger("fetch_openasl")


# ---------------------------------------------------------------------------
# Source manifest parsing
# ---------------------------------------------------------------------------

@dataclass
class SourceRow:
    clip_id: str
    youtube_id: str
    start_s: float
    end_s: float
    caption_en: str
    signer_id: str | None


_REQUIRED_COLS = {"clip_id", "youtube_id", "start_seconds",
                  "end_seconds", "caption_en"}


def load_source_manifest(source: str) -> list[SourceRow]:
    """Read a TSV/CSV from a local path or http(s) URL."""
    if source.startswith(("http://", "https://")):
        logger.info("Downloading source manifest from %s", source)
        with urllib.request.urlopen(source, timeout=60) as fh:
            text = fh.read().decode("utf-8")
        handle = io.StringIO(text)
    else:
        path = Path(source).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"Source manifest not found: {path}")
        logger.info("Reading source manifest %s", path)
        handle = path.open("r", encoding="utf-8")

    # Sniff delimiter — accept TSV or CSV.
    sample = handle.read(8192)
    handle.seek(0)
    delim = "\t" if sample.count("\t") > sample.count(",") else ","
    reader = csv.DictReader(handle, delimiter=delim)

    if reader.fieldnames is None:
        raise ValueError("Source manifest has no header row")
    missing = _REQUIRED_COLS - set(reader.fieldnames)
    if missing:
        raise ValueError(
            f"Source manifest is missing required columns: {sorted(missing)}; "
            f"found {reader.fieldnames}"
        )

    rows: list[SourceRow] = []
    for raw in reader:
        try:
            rows.append(SourceRow(
                clip_id=str(raw["clip_id"]).strip(),
                youtube_id=str(raw["youtube_id"]).strip(),
                start_s=float(raw["start_seconds"]),
                end_s=float(raw["end_seconds"]),
                caption_en=str(raw["caption_en"]).strip(),
                signer_id=str(raw["signer_id"]).strip() or None
                if "signer_id" in raw and raw["signer_id"] else None,
            ))
        except (KeyError, ValueError) as exc:
            logger.warning("Skipping malformed row %r: %s", raw, exc)
    logger.info("Loaded %d source rows", len(rows))
    return rows


# ---------------------------------------------------------------------------
# Per-clip fetch + trim
# ---------------------------------------------------------------------------

def _sources_dir() -> Path:
    return corpus_clip_dir("openasl") / "_sources"


def _probe_duration_ms(path: Path) -> int:
    ffprobe = find_ffprobe()
    cmd = [ffprobe, "-v", "error", "-show_entries",
           "format=duration", "-of", "json", str(path)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {path.name}: {result.stderr[:200]}")
    info = json.loads(result.stdout)
    return int(float(info["format"]["duration"]) * 1000)


def _ensure_source_video(youtube_id: str) -> Path:
    """Download the source video once; reuse across clips from the same yid."""
    sources = _sources_dir()
    sources.mkdir(parents=True, exist_ok=True)
    cached = sources / f"{youtube_id}.mp4"
    if cached.is_file() and cached.stat().st_size > 0:
        return cached

    # Reuse the existing helper; it writes into assets/downloads/.
    downloaded = download_source_video(youtube_id)
    # Move/copy into our sources cache so the corpus is self-contained.
    shutil.copy2(downloaded, cached)
    logger.debug("Cached source video %s -> %s", youtube_id, cached)
    return cached


def _trim_clip(source: Path, out: Path, start_s: float, end_s: float) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg = find_ffmpeg()
    duration = max(0.0, end_s - start_s)
    cmd = [
        ffmpeg, "-y",
        "-ss", f"{start_s:.3f}",
        "-i", str(source),
        "-t", f"{duration:.3f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-an",                             # drop audio — we only need video
        str(out),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg trim failed for {out.name}: {result.stderr[-400:]}"
        )


def fetch_one(
    row: SourceRow,
    *,
    skip_existing: bool,
    max_duration_ms: int,
) -> dict | None:
    """Process one row → manifest dict (or ``None`` on skip / failure)."""
    out_clip = corpus_clip_dir("openasl") / f"{row.clip_id}.mp4"
    duration_target_ms = int((row.end_s - row.start_s) * 1000)
    if duration_target_ms <= 0:
        logger.warning("Row %s has non-positive duration %dms — skip",
                       row.clip_id, duration_target_ms)
        return None
    if duration_target_ms > max_duration_ms:
        logger.info(
            "Row %s exceeds max_clip_duration_ms (%d > %d) — skip",
            row.clip_id, duration_target_ms, max_duration_ms,
        )
        return None

    if skip_existing and out_clip.is_file() and out_clip.stat().st_size > 0:
        logger.debug("Resume: clip %s already on disk — skip", row.clip_id)
        try:
            actual_ms = _probe_duration_ms(out_clip)
        except Exception:
            actual_ms = duration_target_ms
        return _manifest_entry(row, out_clip, actual_ms)

    t0 = time.monotonic()
    try:
        source = _ensure_source_video(row.youtube_id)
        _trim_clip(source, out_clip, row.start_s, row.end_s)
        actual_ms = _probe_duration_ms(out_clip)
    except Exception as exc:
        logger.error("Row %s (%s) failed: %s", row.clip_id, row.youtube_id, exc)
        return None
    logger.info(
        "Fetched %s (%s, %.2fs–%.2fs, %dms) in %.1fs",
        row.clip_id, row.youtube_id, row.start_s, row.end_s, actual_ms,
        time.monotonic() - t0,
    )
    return _manifest_entry(row, out_clip, actual_ms)


def _manifest_entry(row: SourceRow, out_clip: Path, duration_ms: int) -> dict:
    try:
        rel = out_clip.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        rel = out_clip.as_posix()
    return {
        "clip_id": row.clip_id,
        "mp4_path": rel,
        "caption_en": row.caption_en,
        "duration_ms": duration_ms,
        "signer_id": row.signer_id,
        "source": "openasl",
        "youtube_id": row.youtube_id,
        "start_seconds": row.start_s,
        "end_seconds": row.end_s,
    }


# ---------------------------------------------------------------------------
# Output manifest write — load existing, merge, write back
# ---------------------------------------------------------------------------

def _load_existing_manifest(path: Path) -> dict[str, dict]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("Existing manifest %s is corrupt; starting fresh", path)
        return {}
    return {row["clip_id"]: row for row in raw}


def _write_manifest(path: Path, rows_by_id: dict[str, dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(rows_by_id.values(), key=lambda r: r["clip_id"])
    path.write_text(
        json.dumps(ordered, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Fetch the OpenASL corpus into assets/corpus/openasl/.")
    p.add_argument("--source", required=True,
                   help="Path or http(s) URL of the upstream OpenASL "
                        "manifest TSV/CSV (required columns: clip_id, "
                        "youtube_id, start_seconds, end_seconds, "
                        "caption_en; optional: signer_id).")
    p.add_argument("--limit", type=int, default=0,
                   help="Process only the first N rows (0 = all). Use this "
                        "for the week-2 quality gate before committing to "
                        "the full ~150 GB download.")
    p.add_argument("--workers", type=int, default=4,
                   help="Number of parallel fetch+trim workers.")
    p.add_argument("--no-resume", action="store_true",
                   help="Re-download clips even if the mp4 already exists.")
    p.add_argument("--log-level", default="INFO",
                   choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    p.add_argument("--manifest-flush-every", type=int, default=50,
                   help="Persist the running output manifest every N rows.")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    log_path = setup_script_logging(
        "fetch_openasl",
        console_level=getattr(logging, args.log_level),
        file_level=logging.DEBUG,
    )
    logger.info("fetch_openasl starting — log file: %s", log_path)

    settings = get_settings()
    max_ms = settings.retrieval.max_clip_duration_ms
    out_manifest_path = corpus_manifest_path("openasl")
    rows_by_id = _load_existing_manifest(out_manifest_path)
    logger.info("Existing manifest has %d entries", len(rows_by_id))

    source_rows = load_source_manifest(args.source)
    if args.limit > 0:
        source_rows = source_rows[: args.limit]
        logger.info("Limited to first %d rows", args.limit)

    skip_existing = not args.no_resume
    processed = 0
    succeeded = 0
    skipped_existing = sum(
        1 for r in source_rows
        if skip_existing and (corpus_clip_dir("openasl") / f"{r.clip_id}.mp4").is_file()
    )
    logger.info(
        "Plan: %d source rows, %d already on disk (will %sre-fetch)",
        len(source_rows), skipped_existing,
        "" if skip_existing else "still ",
    )

    t_start = time.monotonic()
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futures = {
            ex.submit(fetch_one, row,
                      skip_existing=skip_existing, max_duration_ms=max_ms): row
            for row in source_rows
        }
        for fut in as_completed(futures):
            row = futures[fut]
            processed += 1
            try:
                entry = fut.result()
            except Exception as exc:
                logger.exception("Row %s crashed worker: %s", row.clip_id, exc)
                entry = None
            if entry is not None:
                rows_by_id[entry["clip_id"]] = entry
                succeeded += 1
            if processed % args.manifest_flush_every == 0:
                _write_manifest(out_manifest_path, rows_by_id)
                rate = processed / max(time.monotonic() - t_start, 1e-6)
                logger.info(
                    "Progress: %d/%d processed (%d ok), %.1f rows/s, "
                    "manifest flushed (%d entries)",
                    processed, len(source_rows), succeeded, rate,
                    len(rows_by_id),
                )

    _write_manifest(out_manifest_path, rows_by_id)
    elapsed = time.monotonic() - t_start
    logger.info(
        "Done. processed=%d succeeded=%d total_in_manifest=%d elapsed=%.1fs "
        "(log: %s)",
        processed, succeeded, len(rows_by_id), elapsed, log_path,
    )
    return 0 if succeeded > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
