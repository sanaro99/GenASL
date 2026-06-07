"""Week-2 retrieval-quality gate (Phase 4).

Loads the hand-curated ``tests/fixtures/retrieval_eval.json`` chunks,
queries the OpenASL FAISS index for top-3 hits per chunk, and prints
each hit's caption + clip MP4 path so a human can eyeball whether at
least one is "semantically on-target." Pass criterion documented in
``docs/plan/phase-4-corpus-retrieval.md`` Verification: at least
7 out of 10 chunks must have an on-target top-3 to proceed to Phase 5.

This is a *human-in-the-loop* gate, not an automated pass/fail --
ASL semantic match is too subjective for a regex test. The script
also writes a markdown table to
``logs/retrieval_eval-<YYYYMMDD-HHMMSS>.md`` for easy review.

Usage
-----
    python -m scripts.retrieval_eval
    python -m scripts.retrieval_eval --fixture path/to/other.json --k 5
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from src.avatar.retrieval import RetrievalIndex
from src.core.logging import setup_script_logging
from src.core.paths import LOGS_DIR, PROJECT_ROOT

logger = logging.getLogger("retrieval_eval")


_DEFAULT_FIXTURE = Path("tests") / "fixtures" / "retrieval_eval.json"


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fixture", default=str(_DEFAULT_FIXTURE),
                   help="JSON file with [{id, category, text, ...}] entries.")
    p.add_argument("--name", default=None,
                   help="Corpus name (default: settings.retrieval.primary_corpus).")
    p.add_argument("--k", type=int, default=3,
                   help="Top-k hits to report per query.")
    p.add_argument("--log-level", default="INFO",
                   choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    log_path = setup_script_logging(
        "retrieval_eval",
        console_level=getattr(logging, args.log_level),
    )
    logger.info("retrieval_eval starting — log file: %s", log_path)

    fixture_path = Path(args.fixture)
    if not fixture_path.is_absolute():
        fixture_path = PROJECT_ROOT / fixture_path
    if not fixture_path.is_file():
        logger.error("Fixture not found: %s", fixture_path)
        return 2

    chunks = json.loads(fixture_path.read_text(encoding="utf-8"))
    logger.info("Loaded %d eval chunks from %s", len(chunks), fixture_path)

    index = RetrievalIndex(name=args.name)
    logger.info("Querying corpus %r (n=%d) at k=%d", index.name, len(index), args.k)

    md_lines = [
        "# Retrieval eval report",
        f"_Generated {time.strftime('%Y-%m-%d %H:%M:%S')}_",
        "",
        f"Corpus: **{index.name}**  -  Embedder: "
        f"`{index.settings.embedding_model}`  -  k={args.k}",
        "",
        "| # | Category | Query | Top hit caption | Similarity | Clip |",
        "|---|----------|-------|-----------------|-----------:|------|",
    ]

    t0 = time.monotonic()
    for i, chunk in enumerate(chunks, 1):
        text = chunk["text"]
        category = chunk.get("category", "?")
        logger.info("\n[%d/%d] %s  —  %r", i, len(chunks), category, text)
        try:
            hits = index.query(text, k=args.k)
        except Exception as exc:
            logger.error("Query failed for chunk %s: %s", chunk.get("id"), exc)
            md_lines.append(f"| {i} | {category} | `{text}` | _ERROR_ | – | – |")
            continue
        if not hits:
            logger.warning("  no hits")
            md_lines.append(f"| {i} | {category} | `{text}` | _no hits_ | – | – |")
            continue

        for rank, h in enumerate(hits, 1):
            marker = "  *" if rank == 1 else "   "
            logger.info(
                "%s rank=%d sim=%.3f clip=%s\n        caption=%r",
                marker, rank, h.similarity, h.clip_id, h.caption_en,
            )

        top = hits[0]
        md_lines.append(
            f"| {i} | {category} | `{text}` | {top.caption_en} | "
            f"{top.similarity:.3f} | `{top.clip_id}` |"
        )

    elapsed = time.monotonic() - t0
    logger.info("Eval done in %.2fs", elapsed)

    md_lines += [
        "",
        f"_Eval ran in {elapsed:.2f}s over {len(chunks)} chunks._",
        "",
        "## Reviewer checklist",
        "",
        "For each row, judge whether the **top-3** result is "
        "semantically on-target (the script logged all 3 to the console).",
        "Pass criterion (from `docs/plan/phase-4-corpus-retrieval.md`): "
        "at least 7 of 10 chunks have an on-target top-3.",
    ]
    md_path = LOGS_DIR / log_path.name.replace(".log", ".md")
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    logger.info("Markdown report: %s", md_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
