# Phase 5 — Motion Synthesis + NMM

> Builds Stages 5 and 6. After this phase, given a `list[AslPlanSegment]`,
> the pipeline produces a complete `AvatarRenderPlan` v5.0 that the
> Phase 6 three.js consumer plays.

---

## Goal

Implement `MotionSynthStage` (retrieval + interpolation + NMM channel)
and `AvatarTimelineStage` (bundle the final plan). End state: a
`scripts/preview.html` page can load a generated `AvatarRenderPlan` JSON
and visibly animate a VRM avatar through it without limb jitter or
frame gaps.

## Why this phase

This is where the architecture pays off. The interpreter LLM said *what*
to sign; this phase turns that plan into actual motion that respects:
- the user's "every hand pose from a real Deaf-signer" invariant
  (retrieval-anchored),
- the spec for smooth transitions (AI-eligible later, spline now),
- the spec for non-manual markers driven from audio prosody + emotion.

## Dependencies & prerequisites

- Phase 1 (schema), Phase 2 (`AudioAnalysis` for prosody), Phase 3
  (`AslPlanSegment[]`), Phase 4 (`assets/pose_library/`).
- Add to `requirements.txt`:
  ```
  scipy   # for spline interpolation
  ```

---

## Step-by-step implementation

### 1. `src/avatar/motion_synth.py`

```python
def synthesize_motion(
    segments: list[AslPlanSegment],
    library: PoseLibrary,
    settings: AvatarSettings,
) -> list[MotionFrame]: ...
```

Algorithm:

1. **Per segment, per sign token in `sign_sequence`:**
   - If `library.has(token)`: pull its keyframes.
   - Else: skip (and record in a debug list).
2. **Build per-sign timing budget** within the segment window
   `[start_ms, end_ms]`:
   - Total available duration = `end_ms - start_ms - transition_ms × (n_signs - 1)`.
   - Per-sign duration = library duration (clamped to a min/max ratio
     of `sign_default_duration_ms`). If the budget is tight, time-scale
     uniformly.
3. **Concatenate**:
   - For each sign, emit its keyframes at `frame_rate` fps, time-scaled
     into its budget. Use quaternion SLERP between adjacent keyframes
     within a sign.
   - Between consecutive signs, emit a `transition_ms` spline using
     scipy's `slerp`-equivalent on each bone independently. Use the
     last frame of sign N and the first frame of sign N+1 as the
     boundary conditions.
4. **Resample** the whole sequence to a strict frame grid (drop
   duplicate `t_ms`, ensure monotonic).
5. **Hold the rest pose** during gaps between segments (when there's
   silence) — emit one `MotionFrame` per `1/frame_rate` second at rest
   pose, so the avatar visibly idles rather than freezing.

### 2. `src/avatar/nmm.py`

The NMM channel is **rule-based for v1** — Phase 5 doesn't ship a learned
model. The rules combine `AslPlanSegment.nmm_intent` (from the
interpreter LLM) with prosodic envelope:

```python
def synthesize_nmm(
    segments: list[AslPlanSegment],
    analysis: AudioAnalysis,
    settings: AvatarSettings,
) -> list[NmmFrame]: ...
```

For each frame (at `frame_rate` fps) over the full duration:

| ARKit blendshape | Source signal | Formula |
|---|---|---|
| `browInnerUp` | `nmm_intent.brow_raise` | Plateau at intent value during segment window; ease in/out 80 ms |
| `browDownLeft/Right` | wh-question (intent inferred from sign tokens like `WHAT`, `WHERE`) | 0.4 over the sign duration |
| `eyeSquintLeft/Right` | `nmm_intent.eye_squint` | Direct mapping |
| `mouthClose` / `mouthFunnel` / `mouthPucker` | mouth morphemes (advanced, can skip in v1) | 0 for v1 |
| `jawOpen` | RMS envelope normalized × 0.3 | Subtle mouth movement tracking voice |
| `headPitch` (proxy: rotate Head bone) | `nmm_intent.head_nod` | Sine wave of intensity × amplitude during the segment |
| `headYaw` (proxy: rotate Head bone) | `nmm_intent.head_shake` | Sine wave; faster for negation |
| `headRoll` (proxy: rotate Head bone) | `nmm_intent.head_tilt_left/right` | Constant during the segment |

Note: **head rotations are bone rotations** in the VRM rig, so emit
them into the `MotionFrame.bone_rotations["Head"]` channel, not the
`NmmFrame.blendshapes` channel. NmmFrame is strictly face-blendshapes.

Emphasis: for each sign in `emphasis_signs`, scale that sign's frames
to be 1.2× longer (lengthening = ASL emphasis) and bump `browInnerUp`
by +0.2 during them.

### 3. `src/avatar/vrm_schema.py`

A small module with constants and helpers consumed by both the Python
synthesiser and the three.js consumer (it's also documentation):

```python
VRM_HUMANOID_BONES = ["Hips", "Spine", "Chest", ...]
ARKIT_BLENDSHAPES = ["browInnerUp", "browDownLeft", ...]   # 52 names
REST_POSE: dict[str, list[float]] = {...}                  # identity quats per bone
def rest_motion_frame(t_ms: int) -> MotionFrame: ...
```

### 4. `src/pipeline/stages/motion_synth.py`

```python
class MotionSynthStage(Stage[MotionSynthInput, MotionSynthOutput]):
    name = "motion_synth"
    output_model = MotionSynthOutput

    def __init__(self, settings, cache_root=None):
        super().__init__(settings, cache_root)
        self.library = PoseLibrary()  # lazy-loads JSON on access

    def fingerprint(self, inp):
        s = self.settings.avatar
        # PoseLibrary version: hash the manifest mtime so library
        # rebuilds invalidate cache.
        return stable_hash([
            "motion_synth", s.frame_rate, s.sign_default_duration_ms,
            s.transition_ms,
            *[(seg.chunk_id, tuple(seg.sign_sequence)) for seg in inp.segments],
        ])

    def process(self, inp):
        motion = synthesize_motion(inp.segments, self.library, self.settings.avatar)
        # NMM needs analysis too — see note in Phase 5 wiring below.
        return MotionSynthOutput(
            motion=motion,
            nmm=[],   # filled by AvatarTimelineStage which has analysis access
            duration_ms=max((f.t_ms for f in motion), default=0),
        )
```

### 5. `src/pipeline/stages/avatar_timeline.py`

```python
class AvatarTimelineStage(Stage[AvatarTimelineInput, AvatarRenderPlan]):
    name = "avatar_timeline"
    output_model = AvatarRenderPlan

    def fingerprint(self, inp):
        return stable_hash([
            "avatar_timeline",
            inp.run_id, inp.video_id,
            len(inp.motion), len(inp.nmm), inp.duration_ms,
        ])

    def process(self, inp):
        # NMM finalisation lives here so analysis is accessible.
        nmm = inp.nmm or synthesize_nmm(
            inp.plan_segments,
            inp.analysis,
            self.settings.avatar,
        )
        return AvatarRenderPlan(
            run_id=inp.run_id, video_id=inp.video_id,
            generated_at=now_iso(),
            duration_ms=inp.duration_ms,
            frame_rate=self.settings.avatar.frame_rate,
            motion=inp.motion, nmm=nmm,
            plan_segments=inp.plan_segments,
            debug={
                "analysis": inp.analysis.model_dump() if inp.analysis else None,
                "provider": inp.provider, "model": inp.model,
            },
        )
```

### 6. Wire into `pipeline_avatar.py`

Now `run()` can fully execute. Replace the `NotImplementedError` with
the linear stage chain:

```python
def run(self, video_id, *, use_cache=True):
    ingest = self.audio_ingest.run(AudioIngestInput(video_id=video_id), use_cache=use_cache)
    analyzed = self.audio_analyze.run(AudioAnalyzeInput(...), use_cache=use_cache)
    chunks   = self.semantic_chunk.run(SemanticChunkInput(...), use_cache=use_cache)
    planned  = self.interpreter.run(InterpreterPlanInput(...), use_cache=use_cache)
    motion   = self.motion_synth.run(MotionSynthInput(...), use_cache=use_cache)
    timeline = self.avatar_timeline.run(AvatarTimelineInput(
        run_id=uuid.uuid4().hex[:12],
        video_id=video_id,
        motion=motion.motion, nmm=motion.nmm,
        duration_ms=motion.duration_ms,
        plan_segments=planned.segments,
        analysis=analyzed.analysis,
        provider=planned.provider, model=planned.model,
    ), use_cache=use_cache)
    return timeline
```

### 7. `scripts/preview.html`

A standalone viewer for validating output before Phase 6 lands. Uses
three.js + @pixiv/three-vrm from a CDN. Drag-and-drop an
`avatar_plan_<id>.json` file; renders the avatar going through it.
~200 lines of HTML + JS; commit it.

---

## Tests to add

`tests/test_motion_synth.py`:

1. `test_synthesize_motion_emits_frames_at_frame_rate` — synth plan
   with one segment, mock `PoseLibrary` returning one sign with 5
   keyframes; assert frame count ≈ duration_ms / (1000 / frame_rate)
   within ±2.
2. `test_missing_signs_are_skipped` — plan with `sign_sequence=["HELLO",
   "XYZZY"]`; only HELLO in mock library; assert motion produced
   for HELLO duration only.
3. `test_transitions_use_slerp` — two signs with different endpoint
   poses; assert intermediate frames are between them (no jump).
4. `test_emphasis_lengthens_sign` — same sign, with vs. without in
   `emphasis_signs`; assert with-version produces ≈ 1.2× as many frames.
5. `test_nmm_brow_raise_for_intent` — segment with `nmm_intent.brow_raise=0.8`;
   assert NMM frames in that window have `browInnerUp ≈ 0.8`.
6. `test_full_pipeline_smoke` — wire the whole pipeline with all stages
   mocked (FakeProvider, fake PoseLibrary, synthetic audio analysis),
   assert end-to-end `AvatarRenderPlan` has the right shape.

---

## Verification

```bash
pytest tests/test_motion_synth.py -v

# End-to-end smoke (requires Phases 2–4 done and pose_library/ populated)
python -m src.pipeline.run_pipeline 31y2Bq1RYQA

# Inspect output
ls logs/avatar_plan_*.json
python -c "
import json, pathlib
p = sorted(pathlib.Path('logs').glob('avatar_plan_*.json'))[-1]
d = json.load(open(p))
print(f\"duration={d['duration_ms']}ms, motion={len(d['motion'])} frames, \"
      f\"nmm={len(d['nmm'])} frames, plan_segs={len(d['plan_segments'])}\")
\"

# Visual sanity: open scripts/preview.html in a browser, drag-drop the JSON
```

Pass criteria:
- Frame count matches `duration_ms × frame_rate / 1000` ± 5.
- No `bone_rotations` quaternion has magnitude < 0.95 or > 1.05.
- `nmm` array has the same length as `motion`.
- The avatar visibly moves through recognisable signs in `preview.html`
  with no limb teleportation or T-pose flashes.

---

## Commit hygiene

1. `feat(avatar): vrm_schema bone + blendshape constants`
2. `feat(avatar): retrieval + spline motion synthesizer`
3. `feat(avatar): rule-based NMM from prosody + plan intent`
4. `feat(pipeline): wire MotionSynthStage + AvatarTimelineStage`
5. `feat(pipeline): full InterpreterAvatarPipeline.run() implementation`
6. `feat(scripts): preview.html standalone VRM viewer for validation`
7. `test(avatar): motion synth + NMM coverage`

---

## Hand-off notes

- **NMM placement (face vs. bones) is a common source of bugs.** Re-read
  the table in step 2 above. `headPitch/Yaw/Roll` are bone rotations on
  `Head`, not blendshapes. ARKit blendshapes are face-only.
- **Quaternion conventions:** VRM uses `[x, y, z, w]`. three.js uses
  the same order via `.set(x, y, z, w)`. Keep it consistent in the JSON.
- **Idle pose between segments.** Don't let the avatar freeze on the
  last frame of a sign when there's silence — emit rest-pose frames.
  This is the difference between "looks alive" and "looks broken".
- **Performance:** a 60 s clip at 30 fps = 1 800 frames. Each frame has
  ~25 bones × 4 floats + ~52 blendshapes × 1 float. JSON size ≈ 1–2 MB
  per minute. Acceptable for the prototype; Phase 6 will gzip if needed.

---

## Open questions

- Should classifier predicates (CL:1, CL:3, etc.) get special handling?
  v1 decision: skip — they're not in the pose library.
- Should the synthesiser blend NMM intent values across overlapping
  segments? v1 decision: hard cut at segment boundaries; revisit after
  visual inspection.
