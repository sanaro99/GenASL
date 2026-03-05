# Asset QA & Privacy Notes

> **Project:** GenASL — AI-Powered ASL Overlay Generator (Student POC)
> **Sprint:** 2 — Asset Acquisition & Pipeline Enrichment
> **Last updated:** 2026-03-04

---

## Raw Source Clip Deletion

**Deletion timestamp:** 2026-03-04T00:00:00Z

Per the project privacy policy, all raw source video clips downloaded from YouTube
via the WLASL dataset have been deleted from `assets/raw/`. Intermediate trimmed
clips in `assets/trimmed/` have also been deleted.

### What was deleted

- **30 raw clips** in `assets/raw/` (downloaded YouTube videos, ~175 MB total)
- **21 trimmed clips** in `assets/trimmed/` (intermediate FFmpeg output)

### What is retained

- **50 final standardized clips** in `assets/final/` (A001.mp4–A050.mp4)
  - 320×240 resolution, 25 fps, max 4 seconds duration
  - 29 sourced from WLASL academic dataset, 21 using placeholder
  - All 50 clips passed QA (approved status in manifest)
- **Placeholder templates** in `assets/placeholders/`
- **Asset manifest** at `assets/asset_manifest_v1.json`

### Rationale

Raw source clips were cached only to avoid redundant downloads during the build
process. Once all final clips are built, QA-checked, and the manifest is updated,
the raw and trimmed intermediates serve no further purpose. Deleting them:

1. Reduces disk footprint (~175 MB → ~1 MB)
2. Complies with data minimization principles
3. Avoids retaining full-length YouTube videos beyond what is needed for the
   word-level ASL sign excerpts

---

## QA Summary

| Metric | Value |
|--------|-------|
| Total assets | 50 |
| QA approved | 50 |
| QA needs review | 0 |
| From WLASL | 29 |
| Placeholder | 21 |

All 50 final clips pass the automated QA checks:
- Duration: 0.5–5.0 seconds ✓
- Resolution: 320×240 ✓
- Frame rate: ~25 fps ✓
