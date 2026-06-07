# Phase 4 (archived) — Pose Library (per-gloss WLASL stitching)

> **Superseded** as of 2026-05-24 by
> [`phase-4-corpus-retrieval.md`](phase-4-corpus-retrieval.md). The
> per-gloss WLASL pose library described below is retained as the
> **lexical fallback** for Phase 5 — built only for the ~500 most
> common glosses, not all 2 000 — when both OpenASL phrase retrieval
> and ASL Citizen lexical retrieval miss.
>
> Rationale for the pivot: in motion-synthesis terms, stitching one
> WLASL clip per `sign_sequence` token is Signed English with NMM
> dressing, not proper ASL. See the approved planning memo at
> `C:/Users/sanar/.claude/plans/ok-so-i-rethought-async-cupcake.md`.
> The rest of this document still describes the (now-fallback) build
> correctly.

---

# Phase 4 — Pose Library (offline asset build)

> A one-shot offline script that processes the WLASL clip directory
> with mediapipe and writes per-gloss joint-angle JSON to
> `assets/pose_library/`. The motion synthesiser (Phase 5) reads from
> this directory at runtime.

---

## Goal

Convert `assets/wlasl_clips/` (~2 000 Deaf-signer clips) into
`assets/pose_library/<gloss>.json`, one file per gloss, each containing
keyframe motion data the avatar can replay on a VRM rig.

## Why this phase

The whole architecture rests on the invariant that *every hand pose
traces back to a real Deaf-signer recording*. The pose library is the
asset that makes that invariant operational.

## Dependencies & prerequisites

- WLASL clips present under `assets/wlasl_clips/` (or wherever
  `settings.paths.wlasl_clips` points). The current `assets/words/`
  may already have them; verify before starting.
- `assets/word_manifest.json` mapping `gloss → clip path(s)` is in place.
- Add to `requirements.txt`:
  ```
  mediapipe>=0.10
  opencv-python
  numpy
  ```
- ~30 GB of free disk space during processing; ~50 MB after (JSON only).
- Runtime: ~2–4 hours on CPU for 2 000 clips (~5 s each at 25 fps).

---

## Step-by-step implementation

### 1. `src/avatar/pose_extractor.py`

Mediapipe-Holistic wrapper that processes one video and returns a
list of `MotionFrame`-shaped dicts.

```python
def extract_pose_from_clip(
    clip_path: Path,
    target_fps: int = 30,
    preferred_signer_id: int | None = None,
) -> list[dict]: ...
```

Inside:

1. Open clip with `cv2.VideoCapture`.
2. Sample at `target_fps` (skip frames as needed for higher-fps source).
3. For each sampled frame, run `mp.solutions.holistic.Holistic` with
   `static_image_mode=False, model_complexity=1`.
4. From the result, extract:
   - 33 pose landmarks (world coords)
   - 21 left-hand + 21 right-hand landmarks (world coords)
   - 468 face landmarks (used for the NMM channel later)
5. Convert landmarks to **VRM humanoid bone rotations** using a small
   IK solver. The two viable approaches:
   - **Direct mapping (simpler):** for each VRM bone, compute the
     rotation as the rotation that aligns its rest-pose direction with
     the vector between two relevant landmarks (e.g., LeftUpperArm =
     rotation from rest to (LEFT_SHOULDER → LEFT_ELBOW) direction).
   - **Library (better):** use [`pose2sim`](https://github.com/perfanalytics/pose2sim)
     or a similar pose-to-rig retargeter. Defer this until v1.1; the
     direct mapping is fine for the prototype.
6. Bake to keyframes at the **20% / 40% / 60% / 80% / 100%** time
   points of the clip (5 frames per sign — keeps the library tiny and
   the runtime interpolation smooth).

VRM bone list (must use these exact names — they match @pixiv/three-vrm):

```
Hips, Spine, Chest, UpperChest, Neck, Head,
LeftShoulder, LeftUpperArm, LeftLowerArm, LeftHand,
RightShoulder, RightUpperArm, RightLowerArm, RightHand,
(Left|Right)Thumb(Metacarpal|Proximal|Distal),
(Left|Right)(Index|Middle|Ring|Little)(Proximal|Intermediate|Distal),
LeftUpperLeg, LeftLowerLeg, RightUpperLeg, RightLowerLeg
```

Lower-body bones get static rest-pose quaternions (the avatar sits still
from the waist down).

### 2. `scripts/build_pose_library.py`

Top-level offline build script. Pseudocode:

```python
def main():
    settings = get_settings()
    manifest = json.load(open(WORD_MANIFEST))     # {gloss: [clip_paths]}
    out_dir = PROJECT_ROOT / settings.paths.pose_library
    out_dir.mkdir(parents=True, exist_ok=True)

    skipped, written = 0, 0
    for gloss, clip_paths in tqdm(manifest.items()):
        out = out_dir / f"{gloss}.json"
        if out.exists() and not args.force:
            continue
        # Try clips in order; pick the first one that produces a
        # non-degenerate pose track. Honor preferred signer when present.
        chosen = pick_best_clip(clip_paths, settings.build.preferred_signer_ids)
        if chosen is None:
            skipped += 1; continue
        keyframes = extract_pose_from_clip(chosen)
        out.write_text(json.dumps({
            "gloss": gloss,
            "source_clip": str(chosen.relative_to(PROJECT_ROOT)),
            "duration_ms": int(probe_duration_ms(chosen)),
            "keyframes": keyframes,   # list of MotionFrame dicts
        }, indent=2))
        written += 1
    print(f"Wrote {written}, skipped {skipped}")
```

CLI flags: `--force` (re-extract), `--limit N` (debug subset),
`--gloss GLOSS` (single-gloss debug run).

### 3. `src/avatar/pose_library.py` (runtime loader, used by Phase 5)

```python
class PoseLibrary:
    def __init__(self, root: Path | None = None): ...
    def has(self, gloss: str) -> bool: ...
    def get(self, gloss: str) -> PoseLibraryEntry: ...
    @property
    def glosses(self) -> set[str]: ...
```

`PoseLibraryEntry` is a small `BaseModel` with `gloss`, `duration_ms`,
and `keyframes: list[MotionFrame]`. Loads lazily — touch the JSON only
when `get()` is called.

---

## Tests to add

`tests/test_pose_library.py`:

1. `test_loads_known_gloss` — create a temp `pose_library/HELLO.json`
   with one frame, instantiate `PoseLibrary(root=tmp)`, assert `has("HELLO")`
   and `get("HELLO").keyframes[0].bone_rotations["Hips"]`.
2. `test_missing_gloss_returns_false` — assert `has("XYZZY") is False`.
3. `test_extractor_smoke` (skip if mediapipe not installed): run
   `extract_pose_from_clip` on a tiny WAV-paired test clip; assert
   ≥ 3 keyframes and all bone names appear.

Don't test the build script directly — it's a long-running CLI.

---

## Verification

```bash
# Tiny smoke run (5 glosses, ~30 s)
python scripts/build_pose_library.py --limit 5

# Inspect one output
python -c "import json; d=json.load(open('assets/pose_library/HELLO.json')); print(len(d['keyframes']), 'frames'); print(list(d['keyframes'][0]['bone_rotations'].keys())[:5])"

# Full run (allow several hours)
python scripts/build_pose_library.py

# Final tally
ls assets/pose_library/ | wc -l
# Expected: roughly 1500–2000 .json files (some clips will fail mediapipe)
```

Quality check (sample 10 glosses, eyeball in Phase 5's preview.html):

```bash
python scripts/build_pose_library.py --gloss HELLO --gloss THANK_YOU \
    --gloss LIBRARY --gloss WHERE --gloss WHY --gloss YES --gloss NO \
    --gloss HAPPY --gloss WORK --gloss SCHOOL --force
```

Then in Phase 5's standalone preview, scroll through these and confirm
each looks like a recognisable sign.

---

## Commit hygiene

1. `feat(avatar): mediapipe-based pose extractor for WLASL clips`
2. `feat(scripts): build_pose_library.py — offline asset build`
3. `feat(avatar): runtime PoseLibrary loader`
4. `chore(assets): commit pose_library/ (small JSON — ~50MB)`
5. `test(avatar): pose library loader + extractor smoke`

The `chore(assets)` commit is the big one (~2 000 JSON files). It's
acceptable in this repo because each JSON is small and diff-friendly,
and the alternative — running mediapipe at first run — adds a 2-hour
dependency to every fresh clone.

---

## Hand-off notes

- **The IK / retargeting step is the only research-y part of this phase.**
  Start with the direct-mapping approach. Save complexity for v1.1.
- **Signer selection matters.** `preferred_signer_ids` (already in
  config) lets you pick a signer with consistent framing and good
  visibility. Honor that — bad framing produces poor pose tracks even
  with mediapipe.
- **WLASL coverage is ~2 000 glosses.** Real conversational ASL needs
  more. Document this limitation in the README; gracefully skip missing
  signs at runtime (Phase 5) with a debug note rather than crashing.
- **Face landmarks** are extracted but *not used* by this phase — Phase 5
  drives NMMs from prosody, not from face tracking. Store the face
  keypoints in the JSON anyway (under `face_landmarks: [...]`) so a
  future phase can use them.

---

## Open questions

- Should we add classifier handshape variants per gloss? Decision: not
  in v1. The pose library is one keyframe sequence per gloss.
- Should we ship a Dockerfile for the build script? Decision: not yet.
  If contributors hit mediapipe install pain on Windows, add it then.
