"""Word-level clip lookup — maps ASL gloss words to video clip paths.

Reads ``assets/word_manifest.json`` and provides fast gloss → clip-path
resolution for the word-chaining pipeline.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_WORD_MANIFEST_PATH = _PROJECT_ROOT / "assets" / "word_manifest.json"


class WordLookup:
    """Maps ASL gloss words to their video clip file paths."""

    def __init__(self, manifest_path: Path | None = None) -> None:
        path = manifest_path or _WORD_MANIFEST_PATH
        if not path.is_file():
            raise FileNotFoundError(
                f"Word manifest not found at {path}. "
                "Run: python scripts/build_word_assets.py"
            )

        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        # Build gloss → entry lookup (only non-placeholder entries)
        self._lookup: dict[str, dict] = {}
        self._all_lookup: dict[str, dict] = {}  # includes placeholders
        for word in data.get("words", []):
            gloss = word["gloss"].upper()
            self._all_lookup[gloss] = word
            if word.get("source") != "placeholder":
                self._lookup[gloss] = word

        logger.info(
            "WordLookup loaded: %d real clips, %d total (incl. placeholders)",
            len(self._lookup), len(self._all_lookup),
        )

    @property
    def available_glosses(self) -> set[str]:
        """Set of gloss words that have real (non-placeholder) clips."""
        return set(self._lookup.keys())

    def lookup(self, gloss: str) -> dict | None:
        """Look up a single gloss word.

        Returns the manifest entry dict if a real clip exists, else None.
        """
        return self._lookup.get(gloss.upper())

    def lookup_sequence(self, glosses: list[str]) -> list[dict]:
        """Look up a sequence of gloss words and return found entries.

        Parameters
        ----------
        glosses : list[str]
            Ordered list of ASL gloss words.

        Returns
        -------
        list[dict]
            List of dicts with keys: gloss, found (bool), file_path, duration_ms.
            Only entries where ``found=True`` have valid clip data.
        """
        results = []
        for g in glosses:
            g_upper = g.upper()
            entry = self._lookup.get(g_upper)
            if entry:
                results.append({
                    "gloss": g_upper,
                    "found": True,
                    "word_id": entry["word_id"],
                    "file_path": entry["file_path"],
                    "duration_ms": entry.get("duration_ms", 0),
                    "abs_path": str(_PROJECT_ROOT / entry["file_path"]),
                })
            else:
                results.append({
                    "gloss": g_upper,
                    "found": False,
                    "word_id": None,
                    "file_path": None,
                    "duration_ms": 0,
                    "abs_path": None,
                })

        found_count = sum(1 for r in results if r["found"])
        logger.info(
            "Word lookup: %d/%d glosses resolved (%s)",
            found_count, len(glosses),
            " ".join(g.upper() for g in glosses),
        )
        return results
