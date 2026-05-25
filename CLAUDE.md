# CLAUDE.md — Working in this repository

This file gives any AI assistant (Claude Code, Cursor, etc.) the
minimum context needed to make good edits here. **Read it once per
session, then defer to the canonical docs it points to.**

---

## What this project is

GenASL is an AI pipeline that produces a **3D ASL interpreter avatar**
overlay for YouTube videos. It mimics how a human interpreter works:
listen → analyse emotion + prosody → decide signing strategy with an
LLM → drive a Ready Player Me VRM avatar in the browser via three.js.

> **Status:** prototype in build-out. Phase 1 (bootstrap) is shipped;
> Phases 2–7 are pending and have detailed plans under `docs/plan/`.

---

## Read these before editing

In this order:

1. **[`README.md`](README.md)** — what the project does and how to run it.
2. **[`docs/architecture-overview.md`](docs/architecture-overview.md)** — canonical technical reference.
3. **[`docs/plan/README.md`](docs/plan/README.md)** — implementation roadmap; if you're working a specific phase, also read the matching `docs/plan/phase-N-*.md`.
4. **[`business/feasibility-study/01-technology-feasibility.md`](business/feasibility-study/01-technology-feasibility.md)** — why this architecture and not the others.

If those four contradict this file, **the docs win**; flag the
inconsistency and ask before reconciling.

---

## Non-negotiable invariants

These come from the feasibility study and the user's explicit instructions.
Violating them invalidates the work.

1. **No word-level ASL output.** Word-level gloss is a *valid internal
   representation* inside `AslPlanSegment.sign_sequence`, but it is
   **never surfaced to the user**. The Chrome extension never shows
   gloss text. We do not ship the old WLASL clip-stitching pipeline.

2. **Phrase-level retrieval-augmented, not pure generative.** Tightened
   on 2026-05-24: every output segment's motion comes from a Deaf-signer
   recording, *and the default tier is a continuous clip retrieved at
   phrase level* from `assets/corpus/openasl/` (with ASL Citizen as a
   lexical secondary). Per-gloss WLASL stitching from
   `assets/pose_library/` is the last-resort fallback, always tagged
   `fidelity="stitched"` (or `"degraded"` if > 50% of glosses miss).
   AI orchestrates known-good primitives; generative steps only fill
   *transitions* and *NMM augmentation on top of* the retrieved face.
   If a phase implementation makes this invariant un-verifiable after
   the fact, the phase plan is wrong — flag it before shipping.

3. **Platform-agnostic and platform-pays.** The B2B monetization model
   is platforms paying for the SDK, not end users paying for access.
   Do not add consumer paywalls or restrict accessibility behind a
   user-tier gate. Free for Deaf-led orgs is non-negotiable.

4. **Per-stage disk cache or it doesn't ship.** Every pipeline stage
   subclasses `Stage[InT, OutT]` from `src/pipeline/stages/base.py`
   and implements a deterministic `fingerprint()`. Reruns must be
   JSON-read fast.

5. **Pydantic models, not dicts, between stages.** The schema in
   `src/pipeline/models.py` is authoritative; new fields land there.
   Bump `schema_version` only on a breaking change to `AvatarRenderPlan`
   (current target: `5.1` once Phase 5 lands with the retrieval
   metadata fields).
   
6. **Market expansion, not substitution.** GenASL serves the underserved — content that today has no ASL at all because human interpretation isn't economically viable for it. Human interpreters remain the gold standard for live, high-stakes, nuanced settings, and broader ambient ASL exposure created by GenASL increases demand and visibility for their work. Public-facing copy must reflect this: we expand the pie, we don't take a slice from interpreters.

---

## Repository layout (essential bits only)

```
src/
├── api/server.py               # /health, /asl/avatar
├── audio/
│   ├── source_video.py         # yt-dlp source MP4 (Stage 1 input)
│   └── ...                     # Phase 2 lands extractor, asr, prosody, emotion, analyzer
├── interpreter/                # Phase 3 — chunker, prompt, planner
├── avatar/                     # Phase 4–5 — retrieval, pose extractor, vrm retarget,
│                               # motion synth, NMM, vrm schema
├── core/
│   ├── config.py               # Pydantic Settings; get_settings() singleton
│   ├── paths.py                # all filesystem paths
│   ├── ffmpeg.py               # find_ffmpeg / find_ffprobe
│   └── logging.py
├── llm/providers/              # Ollama / Gemini / OpenAI; one chat() method
├── pipeline/
│   ├── models.py               # v5.0 Pydantic schema (authoritative)
│   ├── pipeline_avatar.py      # InterpreterAvatarPipeline orchestrator
│   ├── run_pipeline.py         # CLI entry
│   ├── io.py                   # save_avatar_plan + print_summary
│   └── stages/
│       ├── base.py             # Stage[InT, OutT] ABC + cache
│       └── ...                 # concrete stages land per phase plans
chrome-extension/               # MV3; Phase 6 wires three.js + VRM
docs/{architecture-overview, plan/, ...}
business/{README, feasibility-study/}
```

---

## Common commands

```bash
# Tests
pytest tests/ -v

# Run the pipeline CLI on a YouTube video ID
python -m src.pipeline.run_pipeline 31y2Bq1RYQA

# Run the local API server
python -m src.api.server                       # http://127.0.0.1:8794
curl http://127.0.0.1:8794/health
```

`config.yaml` (root) overrides Pydantic defaults from `src/core/config.py`.
API keys (`GEMINI_API_KEY`, `OPENAI_API_KEY`) come from the environment,
never from config.

---

## Conventions

- **Stages live in `src/pipeline/stages/<name>.py`**, one class per
  file, `name` class-var = snake_case matching the filename.
- **Domain logic** (the heavy lifting a stage delegates to) goes under
  `src/{audio,interpreter,avatar}/` so stages stay thin and testable.
- **Tests** mirror module paths: `tests/test_<module>.py`. New stage
  tests follow `tests/test_stage_cache.py`. Integration smoke tests
  follow `tests/test_avatar_pipeline_bootstrap.py`.
- **LLM access** goes through `src.llm.providers.make_provider`.
  Never import `openai` directly outside the providers dir.
- **Paths** import from `src.core.paths`, never re-derive with
  `Path(__file__).parents[N]`.
- **Heavy library imports** (faster-whisper, librosa, mediapipe) are
  lazy — inside functions, not at module top-level — so importing a
  module is free for tests that don't exercise it.
- **One-line module docstrings** on the first line stating purpose
  and phase of origin.

---

## What NOT to do

- ❌ Resurrect the gloss pipeline. v4.0 schema, `Pipeline` class,
  `compose_pip`, `transcript_ingestion`, and the WLASL clip-chaining
  code are gone deliberately. Git history preserves them; don't
  cherry-pick back into the active tree.
- ❌ Build a consumer payment tier or premium toggle. Platforms pay.
- ❌ Add a `mode` toggle returning to word-level output. There is one
  pipeline mode now.
- ❌ Ship a pure-neural sign synthesiser (SignDiff/T2S-GPT style)
  without the retrieval anchor. The corpus is the moat.
- ❌ Auto-install dependencies, modify `cookies.txt`, or commit secrets.
  `cookies.txt` is tracked but session-refresh diffs to it should be
  reverted, not pushed.
- ❌ Edit `src/pipeline/models.py` shapes without bumping
  `schema_version` if it would break the extension's JSON consumer.
- ❌ Skip the `fingerprint()` on a new stage. "It's just a prototype"
  is not an excuse; cache invariants are load-bearing.

---

## When something is unclear

1. Check `docs/architecture-overview.md` — it's the canonical reference.
2. Check the matching `docs/plan/phase-N-*.md` for the phase you're in.
3. Check the feasibility study under `business/feasibility-study/`
   for the *why*.
4. If still unclear, leave a `# TODO(phaseN-clarify):` comment and a
   brief note in the phase doc's **Open questions** section. Ship the
   rest; don't block.

---

## Phase status (mirror of `docs/plan/README.md`)

| Phase | Status |
|-------|--------|
| 1 — Bootstrap | **Done** |
| 2 — Audio backbone | **Done** |
| 3 — Interpreter brain | **Done** |
| 4 — Corpus retrieval (OpenASL + ASL Citizen; WLASL fallback) | Pending |
| 5 — Motion synthesis (retrieval-driven) + NMM | Pending |
| 6 — Chrome extension VRM | Pending |
| 7 — API + end-to-end | Pending |

When you ship a phase, update **both** this table and
`docs/plan/README.md`.
