# GenASL — Implementation Roadmap

This directory is the **AI-readable implementation plan** for the GenASL
interpreter-avatar pipeline. Each phase document is self-contained: a fresh
contributor (human or AI) should be able to open one phase doc, follow it
top-to-bottom, and ship the phase without re-deriving context.

---

## Read in this order

1. **[`../architecture-overview.md`](../architecture-overview.md)** — full
   technical reference. **Read this first.**
2. **[`../../business/feasibility-study/`](../../business/feasibility-study/)**
   — strategic and architectural rationale (why this design, not the others).
3. **[`00-architecture.md`](00-architecture.md)** — quick index of what each
   phase delivers and how the phases compose.
4. **Phase doc you're working on** — implementation specifics.

---

## Phase status board

| Phase | Title | Status | ETA from start | Lands files under |
|-------|-------|--------|----------------|-------------------|
| [1](phase-1-bootstrap.md) | Bootstrap — config + schema + skeleton | **Done** | ½ day | `src/{core,pipeline}` |
| [2](phase-2-audio-backbone.md) | Audio backbone | **Done** | ~1 week | `src/audio/`, 2 stages |
| [3](phase-3-interpreter-brain.md) | Interpreter brain | **Done** | ~1 week | `src/interpreter/`, 2 stages |
| [4](phase-4-pose-library.md) | Pose library (offline asset build) | Pending | ~3 days | `assets/pose_library/`, 1 script |
| [5](phase-5-motion-synthesis.md) | Motion synthesis + NMM | Pending | ~1 week | `src/avatar/`, 2 stages |
| [6](phase-6-chrome-extension-vrm.md) | Chrome extension VRM frontend | Pending | ~1 week | `chrome-extension/avatar.js`, content.js |
| [7](phase-7-api-end-to-end.md) | API endpoint + end-to-end demo | Pending | ~3 days | `src/api/server.py`, demo polish |

Total estimated effort: **4–6 focused weeks of solo work**.

---

## How to work a phase

For every phase document below:

1. Read the **Goal** and **Why this phase** sections so you know what
   success looks like.
2. Read the **Dependencies & prerequisites** section and make sure the
   environment is ready (deps installed, prior phases shipped).
3. Follow the **Step-by-step implementation** list.
4. Add tests per the **Tests to add** section.
5. Run the **Verification** checklist top-to-bottom — *do not skip*.
6. Update this `README.md`'s status board.
7. Commit per the **Commit hygiene** notes.

Each phase has a **Hand-off notes** section at the end with known gotchas
and the cross-references most likely to be useful when something breaks.

---

## Non-negotiables that apply to every phase

These come from the feasibility study and are baked into the architecture.
Violating any of them invalidates the work.

| | |
|---|---|
| **No word-level overlay path.** Word-level gloss is fine as an *internal* representation inside `AslPlanSegment.sign_sequence` but never surfaces to the user. The Chrome extension never shows gloss text. |
| **Retrieval-augmented, not pure generative.** Every hand pose in the final motion stream traces back to a Deaf-signer keyframe in `assets/pose_library/`. Generative steps fill transitions and the NMM channel, *not* signs. |
| **Per-stage disk cache or it doesn't ship.** Every stage subclasses `Stage[InT, OutT]` and implements a deterministic `fingerprint()`. Reruns must be JSON reads. |
| **Pydantic models, not dicts, between stages.** The schema in `src/pipeline/models.py` is authoritative; new fields land there. |
| **Platform-pays B2B is the production goal.** Don't add consumer payment surfaces. Don't gate accessibility behind a user paywall. |
| **Deaf-community partnership is mandatory before any external claim of fidelity.** This is a code repo, not a product launch — but the README, marketing copy, and any public demo must say "augmentation, not replacement." |

---

## File-naming and module conventions

- Stages live under `src/pipeline/stages/<name>.py`, one class per file, name = snake_case matching the `name` class-var.
- Domain logic (the heavy lifting a stage delegates to) lives under
  `src/{audio,interpreter,avatar}/` so stages stay thin and testable.
- Tests live under `tests/test_<module>.py`. Stage tests follow the pattern
  in `tests/test_stage_cache.py`; integration tests follow
  `tests/test_avatar_pipeline_bootstrap.py`.
- Each module gets a one-line docstring on the first line stating what it
  does and which phase introduced it.

---

## Where to ask for guidance

If something is ambiguous:

1. Check **[`../architecture-overview.md`](../architecture-overview.md)**
   first — the canonical reference.
2. Check the corresponding feasibility-study section under
   **[`../../business/feasibility-study/`](../../business/feasibility-study/)**.
3. Check `src/pipeline/models.py` for the data shape.
4. If still unclear, leave a `# TODO(phaseN-clarify):` comment in the code
   and a brief note in the phase doc's **Open questions** section — then
   ship the rest.
