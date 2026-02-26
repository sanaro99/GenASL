# Spike Notes — Day 1 Feasibility Tests

> **Project:** GenASL — AI-Powered ASL Overlay Generator (Student POC)
> **Date:** 2026-02-25
> **Sprint:** 1 — Foundation & Feasibility

---

## 1. youtube-transcript-api Test

| Item | Details |
|------|---------|
| **Library version** | youtube-transcript-api 1.2.4 |
| **Test video ID** | E-gGacOpjCA |
| **Test command** | `python -m src.transcript_ingestion.fetcher <VIDEO_ID>` |
| **Result** | _TODO: PASS / FAIL_ |
| **Segments returned** | _TODO: number_ |
| **Notes** | _TODO: any observations — e.g., auto-generated vs. manual captions, language detection issues_ |

### Raw Output (first 5 segments)

```json
TODO: paste JSON output here
```

---

## 2. FAISS + MiniLM Semantic Matching Test

| Item | Details |
|------|---------|
| **Model** | all-MiniLM-L6-v2 (sentence-transformers) |
| **FAISS index type** | IndexFlatIP (cosine similarity via L2-normalised inner product) |
| **Vectors indexed** | _TODO: number (expected: 150 = 50 sentences × 3 variants)_ |
| **Build command** | `python src/matcher/build_index.py` |
| **Build result** | _TODO: PASS / FAIL_ |
| **Sample query** | _TODO: paste a test sentence_ |
| **Top-1 score** | _TODO: e.g., 0.92_ |
| **Matched sentence_id** | _TODO: e.g., S001_ |
| **Notes** | _TODO: observations on match quality, false positives, threshold behaviour_ |

---

## 3. Target YouTube Video

| Item | Details |
|------|---------|
| **Video ID** | _TODO: 11-char ID_ |
| **Title** | _TODO: video title_ |
| **Duration** | _TODO: e.g., 5:32_ |
| **Why chosen** | _TODO: e.g., short explainer video, clear speech, manually uploaded English captions_ |
| **Transcript type** | _TODO: auto-generated / manual_ |
| **Language** | _TODO: en_ |

---

## 4. Blockers Found

| # | Blocker | Severity | Status | Workaround |
|---|---------|----------|--------|------------|
| 1 | _TODO_ | _High/Med/Low_ | _Open/Resolved_ | _TODO_ |
| 2 | _TODO_ | _High/Med/Low_ | _Open/Resolved_ | _TODO_ |

---

## 5. Fallback Options

If a blocker is unresolvable within Sprint 1:

| Scenario | Fallback |
|----------|----------|
| youtube-transcript-api fails or ToS concern | Use a local `.txt` / `.srt` transcript file as input; add a file-based ingestion path |
| MiniLM model too slow on CPU | Use a lighter model (e.g., `all-MiniLM-L12-v1` or `paraphrase-MiniLM-L3-v2`) or reduce batch size |
| FAISS build errors | Fall back to brute-force cosine similarity with scikit-learn `cosine_similarity` |
| No suitable YouTube video found | Create a synthetic test transcript (hardcoded list of dicts) for pipeline testing |

---

## Sign-Off

- [ ] **Team Member 1** reviewed and confirmed results
- [ ] **Team Member 2** reviewed and confirmed results
