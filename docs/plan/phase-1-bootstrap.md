# Phase 1 — Bootstrap

> **Status: DONE.** This document is kept as the reference for what Phase 1
> delivered. New contributors building Phases 2–7 inherit this scaffold.

---

## Goal

Establish the v5.0 schema, config sections, pipeline skeleton, and module
layout so subsequent phases can land stage-by-stage without re-shaping the
project. Existing tests stay green.

## Why this phase

The old codebase was wired around a word-level WLASL clip-stitching pipeline.
This phase replaces the *shape* of the project with the interpreter-avatar
shape — types, settings, orchestrator stub — without yet building any new
runtime behaviour. Stage authors in later phases write *only* their stage
and can plug it in.

---

## What landed

### New / changed source files

| File | Change |
|------|--------|
| [`src/core/config.py`](../../src/core/config.py) | Added `AudioSettings`, `InterpreterSettings`, `AvatarSettings`, `PipelineSettings.use_disk_cache`; expanded `PathsSettings` for new cache dirs. Removed all gloss-pipeline settings. |
| [`src/pipeline/models.py`](../../src/pipeline/models.py) | Schema v5.0: `WordTiming`, `ProsodyFrame`, `EmotionLabel`, `AudioAnalysis`, `InterpreterChunk`, `AslPlanSegment`, `MotionFrame`, `NmmFrame`, `AvatarRenderPlan`, and six stage I/O wrappers. Removed v4.0 models. |
| [`src/pipeline/pipeline_avatar.py`](../../src/pipeline/pipeline_avatar.py) | `InterpreterAvatarPipeline` skeleton; `.run()` raises `NotImplementedError` so callers fail loudly. |
| [`src/pipeline/run_pipeline.py`](../../src/pipeline/run_pipeline.py) | CLI dispatches to `InterpreterAvatarPipeline`. |
| [`src/pipeline/io.py`](../../src/pipeline/io.py) | `save_avatar_plan` + `print_summary` for the new plan model. |
| [`src/pipeline/stages/__init__.py`](../../src/pipeline/stages/__init__.py) | Trimmed to `Stage` + `stable_hash`; concrete stages will be re-exported as they land. |
| [`config.yaml`](../../config.yaml) | New `audio:`, `interpreter:`, `avatar:` sections with safe defaults. |
| [`tests/test_avatar_pipeline_bootstrap.py`](../../tests/test_avatar_pipeline_bootstrap.py) | 5 smoke tests guarding the v5.0 schema, settings, and skeleton behaviour. |

### Deleted (gloss pipeline + dead infra)

`src/gloss/`, `src/transcript_ingestion/`, `src/compositor/`, `src/ui/`,
`src/matcher/`, old pipeline stages (`fetch/translate/lookup/chain/plan.py`),
old `Pipeline` class, old WLASL build scripts, all old docs under `docs/`,
all sprint scripts. Replaced by this docs/plan/ tree.

### Moved

| From | To | Why |
|------|----|-----|
| `src/gloss/providers/` | `src/llm/providers/` | Reused by the interpreter LLM; renamed for clarity. Backwards-compat alias `GlossProvider = LLMProvider` retained. |
| `src/compositor/downloader.py` | `src/audio/source_video.py` | Repurposed as the audio pipeline's Stage 1 input. |

---

## How the bootstrap is verified

Tests (all currently passing — 21 total):

- `tests/test_avatar_pipeline_bootstrap.py` (5 tests) — schema round-trip,
  config-section presence, legacy-key tolerance, skeleton raises.
- `tests/test_stage_cache.py` (5 tests) — `Stage` ABC cache semantics
  still work as Phases 2–5 build on it.
- `tests/test_provider_protocol.py` (11 tests) — provider abstraction
  is intact at its new path.

Run:

```bash
pytest tests/ -v
```

CLI smoke check:

```bash
python -m src.pipeline.run_pipeline 31y2Bq1RYQA
# Expected: exit 4 with log: "Pipeline not fully wired yet — see docs/plan/"
```

Server smoke check:

```bash
python -m src.api.server
# In another shell:
curl http://127.0.0.1:8794/health
# Expected JSON with "ready": false
curl -X POST http://127.0.0.1:8794/asl/avatar -H "Content-Type: application/json" -d '{"video_id":"31y2Bq1RYQA"}'
# Expected: 503 with "phase_status": "Phase 1 (bootstrap) complete; Phases 2–5 pending"
```

---

## Hand-off notes for Phases 2–5

- **Stage authors only edit:** their new stage file under
  `src/pipeline/stages/`, the supporting domain code under
  `src/{audio,interpreter,avatar}/`, the test file under `tests/`,
  and `src/pipeline/pipeline_avatar.py` to wire the stage in. **Do not
  touch `models.py` shapes** without bumping `schema_version`.
- **The `Stage[InT, OutT]` ABC is in `src/pipeline/stages/base.py`** —
  read it before writing your first stage. The cache fingerprint is
  the only non-obvious part.
- **Use `src.llm.providers.make_provider`** for any LLM call. Never
  import `openai` directly.
- **Config defaults must allow `pytest` to run without external services.**
  If a stage needs an API key, the test must use `FakeProvider` or skip
  cleanly when the key is absent.

---

## Open questions

None — Phase 1 closed clean.
