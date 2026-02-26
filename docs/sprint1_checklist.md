# Sprint 1 Sign-Off Checklist

> **Project:** GenASL — AI-Powered ASL Overlay Generator (Student POC)
> **Sprint:** 1 — Foundation & Feasibility
> **Status:** In Review

---

## Technical Completion

| # | Item | Owner | Done |
|---|------|-------|------|
| 1 | `youtube-transcript-api` fetcher implemented with sentence merging and filler-word removal | Sanchit | [ ] |
| 2 | Supported Set CSV (`data/supported_set_v1.csv`) populated with 50 sentences, 3 variants each | Yijie | [ ] |
| 3 | FAISS `IndexFlatIP` index built from all 150 text variants with L2-normalised embeddings | Sanchit | [ ] |
| 4 | Semantic matcher loads index + metadata and returns `action`/`sentence_id`/`score` per segment | Sanchit | [ ] |
| 5 | End-to-end pipeline (`run_pipeline.py`) produces render plan JSON and appends `run_log.jsonl` | Both | [ ] |
| 6 | All unit tests pass (`pytest tests/ -v`) — fetcher (4), matcher (4), integration (1), RAI gate (4) | Both | [ ] |
| 7 | `config.yaml` centralises all tuneable parameters (model name, threshold, paths) | Yijie | [ ] |
| 8 | Sprint 1 verification script (`run_sprint1_verification.sh`) runs end-to-end without errors | Both | [ ] |

---

## RAI Validation

| # | Item | Owner | Done |
|---|------|-------|------|
| 1 | Allowlist-only gate forces `CAPTIONS` for any text not in the 50-sentence Supported Set | Both | [ ] |
| 2 | Confidence threshold (0.80) is enforced — scores below trigger `CAPTIONS` fallback | Both | [ ] |
| 3 | Every `CAPTIONS` fallback emits a `WARNING`-level log with original text and score | Sanchit | [ ] |
| 4 | Suspicious high ASL ratio (> 90%) triggers a pipeline-level warning | Yijie | [ ] |
| 5 | Unsupported use categories documented with risk levels and enforcement mechanisms | Both | [ ] |
| 6 | Disclosure label text ("AI-generated ASL avatar (POC)") finalised and rationale recorded | Both | [ ] |

---

## Sign-Off

| Team Member | Name | Date |
|-------------|------|------|
| **Sanchit** | ___________________ | ____-____-____ |
| **Yijie**   | ___________________ | ____-____-____ |
