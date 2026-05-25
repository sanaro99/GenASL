# Phase 5 — Motion synthesis + NMM (retrieval-driven)

> Builds Stages 5 and 6. After this phase, given a
> `list[AslPlanSegment]`, the pipeline produces a complete
> `AvatarRenderPlan` v5.1 that the Phase 6 three.js consumer plays.
>
> **Architecture shift (2026-05-24):** motion is now sourced from
> *retrieved continuous Deaf-signed clips* (Phase 4's OpenASL +
> ASL Citizen indexes), not from per-gloss WLASL stitching. WLASL
> stitching is retained as the last-resort fallback when both
> retrieval indexes miss. The earlier per-gloss-stitching version of
> this plan is preserved in git history at the commit before this
> pivot.

---

## Goal

Implement `MotionSynthStage` (retrieval-driven, with WLASL fallback)
and `AvatarTimelineStage` (bundle the final plan). End state: a
`scripts/preview.html` page can load a generated `AvatarRenderPlan`
JSON and visibly animate a VRM avatar through it without limb jitter
or frame gaps, with **per-segment fidelity tags** so a Deaf reviewer
can see which segments came from retrieval vs. fallback.

## Why this phase

This is where the architecture pays off. The interpreter LLM said
*what* to sign and the Phase 4 indexes know *who has signed something
like that already*. Phase 5 stitches those two together into a motion
stream whose grammar comes from real Deaf signers, not from English
word order.

## Dependencies & prerequisites

- Phases 1, 2, 3 done; Phase 4 corpus + indexes in place
  (OpenASL primary, ASL Citizen secondary, WLASL fallback).
- Add to `requirements.txt`:
  ```
  scipy   # for spline interpolation on the WLASL fallback path
  ```

---

## Step-by-step implementation

### 1. `src/avatar/motion_synth.py`

```python
def synthesize_motion(
    segments: list[AslPlanSegment],
    indexes: RetrievalChain,
    library: PoseLibrary,         # WLASL fallback
    settings: AvatarSettings,
    retrieval_settings: RetrievalSettings,
) -> tuple[list[MotionFrame], list[AslPlanSegment]]:
    """Returns (motion_frames, annotated_segments).

    annotated_segments mirror the input but with retrieved_clip_id,
    retrieval_similarity, and fidelity tags populated.
    """
```

Algorithm, **per segment**:

1. Build a retrieval query: prefer `segment.notes`-augmented `chunk_text`
   if available (the interpreter brain in Phase 3 will be lightly
   revised in this phase to emit a `query_text` alongside the gloss
   sequence). Fall back to joining `topic_comment` if `query_text` is
   missing.
2. `hits = indexes.query(query_text, k=5)`.
3. **Tier 1 — phrase retrieval (OpenASL):** pick the best hit whose
   `similarity ≥ retrieval_settings.phrase_threshold` (default 0.55)
   **and** whose `duration_ms` is within ±40% of the segment window.
   If found:
   - `poses = indexes.load_poses(hit.clip_id)`
   - Time-scale `poses` linearly into `[seg.start_ms, seg.end_ms]`.
   - Tag `seg.fidelity = "retrieval"`,
     `seg.retrieved_clip_id = hit.clip_id`,
     `seg.retrieval_similarity = hit.similarity`.
4. **Tier 2 — lexical retrieval (ASL Citizen):** for each gloss token
   in `seg.sign_sequence`, query the Citizen index. If a Citizen entry
   is found above `lexical_threshold` (default 0.7) for *every* token,
   concatenate those clips' pose streams with `transition_ms` SLERP
   transitions between them. Tag `seg.fidelity = "lexical"`.
5. **Tier 3 — WLASL gloss stitching (archived Phase 4 path):** for
   each gloss in `seg.sign_sequence`, look it up in the WLASL pose
   library. Use the original per-keyframe SLERP between signs.
   Missing glosses are skipped; if > 50% of glosses are missing, tag
   `seg.fidelity = "degraded"`, else `seg.fidelity = "stitched"`.
6. **Resample** the whole sequence to a strict frame grid at
   `settings.frame_rate` fps.
7. **Hold the rest pose** during gaps between segments — emit one
   `MotionFrame` per `1/frame_rate` second at rest pose so the avatar
   visibly idles rather than freezing.

### 2. `src/avatar/retrieval_chain.py`

Thin orchestrator over the indexes built in Phase 4. One public method:

```python
class RetrievalChain:
    def __init__(self, settings: RetrievalSettings): ...
    def query(self, text: str, k: int = 5) -> list[RetrievalHit]: ...
    def load_poses(self, clip_id: str) -> list[MotionFrame]: ...
```

Internally it picks the right index based on the `clip_id` prefix
(`openasl_*` vs `aslcitizen_*`).

### 3. `src/avatar/nmm.py`

The NMM channel stays **prosody-driven and rule-based** for v1. The
table from the archived Phase 5 plan still applies — `nmm_intent` from
the interpreter LLM combined with the prosodic envelope, mapped to
ARKit blendshapes and Head-bone rotations.

**However**, the priority of the NMM rules changes:

- For `fidelity = "retrieval"` segments, the retrieved clip *already
  contains* the signer's natural NMMs (we extracted face landmarks
  alongside pose). Use those as the base, and only *augment* with
  emphasis/prosody (e.g. bump `browInnerUp` by +0.2 on
  `emphasis_signs`). Don't overwrite the retrieved facial track.
- For `fidelity = "lexical"`, `"stitched"`, or `"degraded"`, the NMM
  channel is purely synthetic per the archived rules.

This means `src/avatar/pose_extractor.py` (Phase 4) must also yield
face landmarks alongside pose. The `MotionFrame` schema already
accommodates this — face data lives in `NmmFrame`, not `MotionFrame`,
and we emit them paired.

### 4. `src/avatar/vrm_schema.py`

Unchanged from the archived plan: VRM bone constants, ARKit blendshape
list, `REST_POSE`, `rest_motion_frame()`.

### 5. `src/pipeline/stages/motion_synth.py`

```python
class MotionSynthStage(Stage[MotionSynthInput, MotionSynthOutput]):
    name = "motion_synth"
    output_model = MotionSynthOutput

    def __init__(self, settings, cache_root=None):
        super().__init__(settings, cache_root)
        self.indexes = RetrievalChain(settings.retrieval)
        self.library = PoseLibrary()   # lazy

    def fingerprint(self, inp):
        s = self.settings
        return stable_hash([
            "motion_synth_v2",                       # bump on the pivot
            s.avatar.frame_rate,
            s.avatar.sign_default_duration_ms,
            s.avatar.transition_ms,
            s.retrieval.phrase_threshold,
            s.retrieval.lexical_threshold,
            s.retrieval.embedding_model,
            self.indexes.index_signature,            # mtime hash
            *[(seg.chunk_id, tuple(seg.sign_sequence), seg.notes)
              for seg in inp.segments],
        ])

    def process(self, inp):
        motion, annotated = synthesize_motion(
            inp.segments, self.indexes, self.library,
            self.settings.avatar, self.settings.retrieval,
        )
        return MotionSynthOutput(
            motion=motion,
            nmm=[],                                  # AvatarTimelineStage fills
            duration_ms=max((f.t_ms for f in motion), default=0),
            annotated_segments=annotated,            # new field
        )
```

### 6. `src/pipeline/stages/avatar_timeline.py`

Same shape as the archived plan, but:

- Reads `annotated_segments` from the motion-synth output and writes
  them through to `AvatarRenderPlan.plan_segments` so the extension
  can render the `fidelity` badge in dev mode.
- For `fidelity = "retrieval"` segments, NMM is the *retrieved-face*
  track plus prosody augmentation; for others, it's purely synthetic.
- `schema_version = "5.1"`.

### 7. Wire into `pipeline_avatar.py`

`run()` becomes fully executable. Same linear chain as the archived
plan; the only new line is constructing `RetrievalChain` once at
pipeline init so the FAISS index loads exactly once per process.

### 8. `scripts/preview.html`

Same standalone viewer as the archived plan, plus:

- A small per-segment HUD showing `fidelity` ("retrieval / lexical /
  stitched / degraded"), `retrieval_similarity`, and the `clip_id` for
  the retrieved source. Hide behind a `?debug=1` query param.

---

## Tests to add

`tests/test_motion_synth.py`:

1. `test_synth_uses_retrieval_when_similarity_high` — `RetrievalChain`
   mock returns one hit with `similarity=0.9`; assert
   `fidelity="retrieval"` and pose frames match the mock's pose stream.
2. `test_synth_falls_through_to_lexical_when_phrase_misses` —
   phrase index returns `similarity=0.3`; lexical index returns hits
   above threshold for every gloss; assert `fidelity="lexical"` and
   one clip per gloss is stitched.
3. `test_synth_falls_through_to_wlasl_when_lexical_misses` — both
   indexes return below-threshold; mock WLASL `PoseLibrary` has the
   glosses; assert `fidelity="stitched"`.
4. `test_synth_marks_degraded_when_most_glosses_missing` — WLASL
   library has only 1 of 4 glosses; assert `fidelity="degraded"`.
5. `test_retrieved_face_preserved_when_present` — `RetrievalHit`
   carries an `nmm_track`; assert the output NmmFrames echo it
   (within 0.05 of the retrieved values) rather than the rule-based
   defaults.
6. `test_full_pipeline_smoke` — wire the whole pipeline with all
   stages mocked (FakeProvider, fake `RetrievalChain`, fake
   `PoseLibrary`, synthetic `AudioAnalysis`); assert end-to-end
   `AvatarRenderPlan` v5.1 has the right shape.

---

## Verification

```bash
pytest tests/test_motion_synth.py -v

# End-to-end smoke (requires Phase 4 indexes built)
python -m src.pipeline.run_pipeline 31y2Bq1RYQA

# Inspect output fidelity distribution
python -c "
import json, pathlib, collections
p = sorted(pathlib.Path('logs').glob('avatar_plan_*.json'))[-1]
d = json.load(open(p))
print(f\"duration={d['duration_ms']}ms, motion={len(d['motion'])} frames\")
print('fidelity:', collections.Counter(s.get('fidelity','?')
                                       for s in d['plan_segments']))
"

# Visual sanity: open scripts/preview.html?debug=1, drag the JSON
```

Pass criteria:

- Frame count matches `duration_ms × frame_rate / 1000` ± 5.
- All `bone_rotations` quaternions have magnitude in `[0.95, 1.05]`.
- ≥ 60% of segments tagged `fidelity="retrieval"` on a typical news
  / instructional clip (else the corpus is too narrow — feed back to
  Phase 4).
- Deaf consultant calls the retrieval-tier output "recognizable as
  ASL with rough edges" on at least 2 of 3 prepared 60-s demos.

---

## Commit hygiene

1. `feat(avatar): RetrievalChain + tiered fallback (openasl→aslcitizen→wlasl)`
2. `feat(avatar): retrieval-driven motion synth + fidelity tagging`
3. `feat(avatar): NMM channel — retrieved face when available, rule-based otherwise`
4. `feat(pipeline): wire MotionSynthStage v2 + AvatarTimelineStage`
5. `feat(pipeline): full InterpreterAvatarPipeline.run() implementation`
6. `feat(scripts): preview.html — debug HUD for fidelity tier`
7. `test(avatar): motion synth + retrieval-fallback coverage`

---

## Hand-off notes

- **Retrieval quality dominates everything.** If the Phase 4 week-2
  gate (≥7/10 hand-curated chunks have an on-target top-3) failed,
  Phase 5 can't fix it. Loop back and either expand the corpus,
  swap the embedding model, or expand the query-rewriter prompt
  with example phrasings.
- **Don't overwrite retrieved face tracks.** The whole point of
  retrieval is that the signer already chose the right NMMs. Only
  augment — don't replace.
- **Idle pose between segments** is the difference between "looks
  alive" and "looks broken." Carry over from the archived plan.
- **Quaternion convention is `[x, y, z, w]`** in both VRM and
  three.js. Keep it consistent in the JSON.

---

## Open questions

- **Cross-signer normalization.** Retrieved clips will jump between
  signers (different proportions, different rest poses). v1 decision:
  accept the jumpiness; revisit with a signer-normalisation pass in
  v1.1.
- **Should classifier predicates ever fall back?** Probably no —
  classifier predicates are *meaningful only* as continuous signing,
  not as a gloss-stitched approximation. Tag them in the interpreter
  brain so the synth stage can choose `fidelity="degraded"` rather
  than try to stitch them.
- **Re-retrieval on cache miss.** When the corpus is updated, the
  fingerprint's `index_signature` invalidates the cache cleanly. But
  the per-clip pose JSON doesn't have to re-embed — it's content-
  addressed by `clip_id`. Confirm the Phase 4 build script writes
  poses idempotently.
