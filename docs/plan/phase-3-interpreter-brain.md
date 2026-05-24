# Phase 3 — Interpreter Brain

> Builds Stages 3 and 4. After this phase, given an `AudioAnalysis`, the
> pipeline produces a structured `list[AslPlanSegment]` — the
> interpreter's plan for what to sign and how to inflect it.

---

## Goal

Implement `SemanticChunkStage` and `InterpreterPlanStage` plus the
supporting domain modules under `src/interpreter/`. End state: an LLM
call produces a validated `AslPlanSegment` per semantic chunk, with
sign sequence, NMM intent, emphasis flags, and (optionally) role shifts.

## Why this phase

This stage is the "brain" — the thing that mimics what an interpreter
*decides* before their hands move. Getting it right is more about
prompt design and structured output validation than about model size.

## Dependencies & prerequisites

- Phase 2 complete (`AudioAnalysis` is available).
- No new third-party deps — uses `src.llm.providers` already in repo.

---

## Step-by-step implementation

### 1. `src/interpreter/chunker.py`

```python
def chunk(analysis: AudioAnalysis, settings: InterpreterSettings) -> list[InterpreterChunk]: ...
```

Algorithm:

1. Reconstruct a "sentence stream" by walking `analysis.asr_words` in
   order, joining with spaces, and inserting candidate boundaries:
   - **Hard boundary:** silence ≥ `audio.vad_min_silence_ms` (gap between
     consecutive `WordTiming.end_ms` and next `start_ms`).
   - **Soft boundary:** punctuation `.`, `?`, `!`, `;` in the word
     (Whisper does emit punctuation when `word_timestamps=True`).
2. Emit a chunk every time we cross a hard boundary OR the running text
   length exceeds `settings.max_chunk_chars` AND a soft boundary is
   present.
3. Skip chunks whose text length < `settings.min_chunk_chars`.
4. For each chunk:
   - Resolve `start_ms` / `end_ms` from the word range.
   - `dominant_emotion`, `emotion_intensity` ← pick the emotion label
     whose span overlaps the chunk centroid.
   - `f0_range_hz` ← (min, max) over voiced prosody frames in the span.
   - `rms_mean` ← mean RMS in the span.
   - `speaking_rate_wps` ← word count / span seconds.
   - `ended_with_pause` ← `True` if the next gap ≥ vad threshold.

### 2. `src/interpreter/prompt.py`

The interpreter persona prompt. Keep this file structured so the prompt
can be iterated independently:

```python
SYSTEM_PROMPT = """You are an ASL interpreter. ..."""
FEW_SHOT_EXAMPLES = [...]
def build_user_prompt(chunk: InterpreterChunk, settings: InterpreterSettings) -> str: ...
```

The system prompt must demand JSON output matching `AslPlanSegment`'s
shape minus the timing fields (which are filled in from the chunk). At
minimum:

```json
{
  "topic_comment": ["TOPIC: ...", "COMMENT: ..."],
  "sign_sequence": ["GLOSS1", "GLOSS2", ...],
  "nmm_intent": {"brow_raise": 0.0..1.0, "head_tilt_left": 0.0..1.0,
                 "head_tilt_right": 0.0..1.0, "head_nod": 0.0..1.0,
                 "head_shake": 0.0..1.0, "mouth_open": 0.0..1.0,
                 "eye_squint": 0.0..1.0},
  "emphasis_signs": ["GLOSS_TO_AMPLIFY", ...],
  "role_shifts": [{"target": "person|object", "signs": ["..."]}],
  "notes": "free-form ≤ 1 sentence"
}
```

Few-shot examples must cover: yes/no question (brow raise), wh-question
(brow furrow), negation (head shake), emphasis (lengthened sign + brow
raise), and a neutral declarative.

### 3. `src/interpreter/planner.py`

```python
def plan_chunks(
    chunks: list[InterpreterChunk],
    settings: InterpreterSettings,
    provider: LLMProvider | None = None,
) -> tuple[list[AslPlanSegment], str, str]:  # segments, provider_name, model
    ...
```

- Call the LLM **per chunk** (do not batch) — keeps prompts short and
  errors localised.
- Parse the LLM output robustly: strip ```json fences, retry once on
  malformed JSON, fall back to a minimal `AslPlanSegment` with just
  the words split as `sign_sequence` and a note "fallback: LLM parse
  failed".
- Validate sign tokens: uppercase, strip whitespace, drop tokens with
  non-ASCII or punctuation.
- Cap `nmm_intent` values to [0, 1].
- Don't filter against the pose library yet — Phase 5 handles missing
  signs at synthesis time.

### 4. `src/pipeline/stages/semantic_chunk.py`

```python
class SemanticChunkStage(Stage[SemanticChunkInput, SemanticChunkOutput]):
    name = "semantic_chunk"
    output_model = SemanticChunkOutput

    def fingerprint(self, inp):
        s = self.settings
        return stable_hash([
            "semantic_chunk",
            inp.analysis.duration_ms,
            len(inp.analysis.asr_words),
            s.interpreter.max_chunk_chars, s.interpreter.min_chunk_chars,
            s.audio.vad_min_silence_ms,
        ])

    def process(self, inp):
        chunks = chunk(inp.analysis, self.settings.interpreter)
        return SemanticChunkOutput(chunks=chunks)
```

### 5. `src/pipeline/stages/interpreter_plan.py`

```python
class InterpreterPlanStage(Stage[InterpreterPlanInput, InterpreterPlanOutput]):
    name = "interpreter_plan"
    output_model = InterpreterPlanOutput

    def fingerprint(self, inp):
        s = self.settings
        # Include the prompt version so prompt edits invalidate the cache.
        from src.interpreter.prompt import PROMPT_VERSION
        return stable_hash([
            "interpreter_plan",
            PROMPT_VERSION,
            s.llm.provider,
            getattr(s.llm, s.llm.provider).model,
            s.interpreter.temperature,
            s.interpreter.include_role_shifts,
            s.interpreter.include_classifiers,
            [c.chunk_id for c in inp.chunks],
            [c.text for c in inp.chunks],
        ])

    def process(self, inp):
        segs, provider, model = plan_chunks(inp.chunks, self.settings.interpreter)
        return InterpreterPlanOutput(segments=segs, provider=provider, model=model)
```

Define `PROMPT_VERSION = "v1"` in `prompt.py` and bump on every meaningful
prompt change.

### 6. Wire into `pipeline_avatar.py`

Add `self.semantic_chunk` and `self.interpreter` stages. `run()` still
raises until Phase 5.

---

## Tests to add

`tests/test_interpreter_planner.py`:

1. `test_chunker_respects_max_chunk_chars` — synthetic `AudioAnalysis`
   with no pauses, long text; assert chunks all ≤ `max_chunk_chars`.
2. `test_chunker_splits_on_pause` — two segments separated by a 1 s gap
   → two chunks.
3. `test_planner_calls_provider_once_per_chunk` — `FakeProvider` that
   counts calls; assert one call per chunk and `provider.name` =
   `"fake"` is returned.
4. `test_planner_handles_malformed_json` — `FakeProvider` returns junk
   on first call, valid JSON on retry; assert one fallback or one retry
   succeeds (whichever your impl chose).
5. `test_planner_clamps_nmm_intents_to_unit_range` — provider returns
   `nmm_intent.brow_raise=1.7`; assert clamped to 1.0.
6. `test_interpreter_stage_fingerprint_includes_prompt_version` — flip
   `PROMPT_VERSION`, assert different cache key.

---

## Verification

```bash
pytest tests/test_interpreter_planner.py -v

# Manual sanity (requires a configured provider — set GEMINI_API_KEY etc.)
python - <<'EOF'
from src.pipeline.models import AudioAnalysis, InterpreterChunk
from src.interpreter.planner import plan_chunks
from src.core.config import get_settings

ch = InterpreterChunk(
    chunk_id="c0", start_ms=0, end_ms=3000,
    text="Where is the library?",
    dominant_emotion="questioning", emotion_intensity=0.7,
    speaking_rate_wps=1.3, ended_with_pause=True,
)
segs, provider, model = plan_chunks([ch], get_settings().interpreter)
print(provider, model, segs[0].model_dump_json(indent=2))
EOF
```

Expected output: a JSON `AslPlanSegment` with `sign_sequence` something
like `["WHERE", "LIBRARY"]` (wh-question word-order varies — accept
either order) and `nmm_intent.brow_raise` > 0 (wh-question signal).

---

## Commit hygiene

1. `feat(interpreter): semantic chunker (VAD + clause boundaries)`
2. `feat(interpreter): persona prompt + few-shots (PROMPT v1)`
3. `feat(interpreter): planner with JSON parsing + validation`
4. `feat(pipeline): wire SemanticChunkStage + InterpreterPlanStage`
5. `test(interpreter): coverage for chunker + planner`

---

## Hand-off notes

- **Prompt iteration is the bulk of the work.** Plan to spend half of
  the phase tuning the prompt against 10–20 hand-curated test sentences
  covering wh-question, yes/no question, negation, emphasis, role shift,
  classifier predicate, narrative aside. Keep that test set in
  `tests/fixtures/interpreter_eval.json`.
- **Don't hand-validate against a fluent ASL signer yet** — that comes
  with the Deaf-community evaluation gate. Phase 3's job is structural
  correctness; phase 7 surfaces output to test users.
- **LLM cost watch:** Gemini 2.0 Flash is essentially free for prototype
  volumes. If you switch to OpenAI gpt-4o-mini, expect ~$0.001 per chunk
  → ~$0.05 for a 60 s video. Don't ship gpt-4o as default.

---

## Open questions

- Should the planner re-call the LLM with the *previous* chunk as
  context (to handle pronouns and role-shift continuity)? Decision:
  defer to v1.1; for v1 each chunk is independent.
- Are classifier predicates worth modeling in v1, or skip them until a
  Deaf advisor signs off? Decision: include them in the schema (already
  done), let the LLM emit them, but don't render them in Phase 5 yet —
  Phase 5 skips any sign token not in the pose library.
