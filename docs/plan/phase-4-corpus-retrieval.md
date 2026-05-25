# Phase 4 — Corpus ingestion + phrase-level retrieval index

> Pivots the project off per-gloss WLASL stitching (the original Phase 4
> plan, archived as [`phase-4-pose-library.md`](phase-4-pose-library.md))
> and onto **phrase-level retrieval** from a continuous Deaf-signed
> corpus — OpenASL as primary, ASL Citizen as a secondary lexical
> fallback, WLASL kept only as a last-resort vocabulary fallback.
>
> Rationale: the original word-stitching path was Signed English with
> NMM dressing. Switching the unit of retrieval to continuous Deaf
> signing gives us proper ASL grammar (topic-comment, classifier verbs,
> role shifts, NMM) *for free*, because a Deaf person already signed
> it. See [`../../C:/Users/sanar/.claude/plans/ok-so-i-rethought-async-cupcake.md`]
> (the approved planning memo) for the full options analysis.

---

## Goal

A reproducible offline pipeline that, given an English text query,
returns the most semantically-aligned continuous-signing clip from a
Deaf-signed corpus, along with the clip's extracted pose stream
retargeted onto a VRM rig.

Concretely the phase ships:

1. `assets/corpus/openasl/` — downloaded clips + captions (kept out of
   git via `.gitignore`; a manifest JSON is tracked).
2. `assets/corpus/openasl_manifest.json` — `{clip_id, mp4_path,
   caption_en, duration_ms, signer_id?}`.
3. `assets/corpus/openasl.faiss` — FAISS index over sentence-transformer
   embeddings of every clip's caption.
4. `assets/corpus/openasl_poses/<clip_id>.json` — per-clip VRM-rig pose
   stream (~30 fps), extracted once with Mediapipe + a small IK
   retargeter.
5. `src/avatar/retrieval.py` — `RetrievalIndex` runtime API.
6. `src/avatar/pose_extractor.py` + `src/avatar/vrm_retarget.py` — the
   one-shot extraction + retargeting code, shared with the WLASL
   fallback path.

## Why this phase

Phase 5 needs *something to play*. The original plan tried to assemble
that motion from per-gloss WLASL keyframes. That output is structurally
Signed English. This phase rebuilds the asset layer so Phase 5 can
instead replay a real Deaf signer's continuous motion, falling back to
gloss stitching only when retrieval misses.

## Dependencies & prerequisites

- Phase 3 done (already shipped). The interpreter brain becomes a
  *query rewriter* in Phase 5; no changes needed in Phase 3 code.
- Disk: OpenASL is ~150 GB raw video. Plan for 200 GB headroom; the
  extracted pose JSON is ~1–2 GB.
- Add to `requirements.txt`:
  ```
  mediapipe>=0.10
  opencv-python
  numpy
  sentence-transformers>=2.7
  faiss-cpu          # or faiss-gpu if available
  ```
- Network: one-time download of the OpenASL corpus from its official
  release URL (see open question below — licensing review).
- Compute: Mediapipe runs CPU at ~real-time per clip. Embedding 50 k
  captions with `all-MiniLM-L6-v2` is ~10 min on a single GPU,
  ~1 hour on CPU. **No model training.**

---

## Step-by-step implementation

### 1. `scripts/fetch_openasl.py`

Downloads the OpenASL corpus from the official release index, mirrors
it to `assets/corpus/openasl/`, and emits the manifest JSON. CLI flags:

- `--limit N` — pull only the first N clips (use this for the week-2
  retrieval-quality gate before committing to the full ~150 GB).
- `--resume` — skip already-downloaded files.
- `--workers K` — parallel downloads.

The manifest entry shape:

```json
{
  "clip_id": "openasl_00042",
  "mp4_path": "assets/corpus/openasl/00042.mp4",
  "caption_en": "the meeting starts at three pm",
  "duration_ms": 4200,
  "signer_id": "s17",
  "source": "openasl_v1.0"
}
```

### 2. `src/avatar/pose_extractor.py` (shared with the WLASL fallback)

Mediapipe-Holistic wrapper. Same surface as the original Phase 4 plan
called for, just retargeted onto continuous-clip input rather than
isolated-sign input:

```python
def extract_pose_stream(
    clip_path: Path,
    target_fps: int = 30,
) -> list[MotionFrame]: ...
```

The function returns one `MotionFrame` per sampled frame — not five
keyframes. For a 4-second clip at 30 fps that's 120 frames; Phase 5
will sub-sample if needed.

Internally:

1. `cv2.VideoCapture` + frame stride to hit `target_fps`.
2. `mediapipe.solutions.holistic.Holistic(model_complexity=1)` per
   frame → pose / left-hand / right-hand / face landmarks.
3. Hand into `vrm_retarget.landmarks_to_vrm_bones(...)`.
4. Yield a `MotionFrame(t_ms, bone_rotations, position=[0,0,0])`.

### 3. `src/avatar/vrm_retarget.py`

Small IK / direct-mapping module that turns Mediapipe world-coord
landmarks into VRM humanoid bone rotation quaternions (`[x, y, z, w]`).
Same VRM bone list as the archived Phase 4 doc — that part doesn't
change.

Start with **direct mapping** (compute each bone's rotation as the
rotation that aligns its rest-pose direction with the vector between
two relevant landmarks). Defer a library-based retargeter (`pose2sim`
etc.) to v1.1.

### 4. `scripts/build_corpus_index.py`

Offline build script:

```python
def main():
    settings = get_settings()
    manifest = json.load(open(MANIFEST_PATH))
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    embeddings = model.encode([c["caption_en"] for c in manifest],
                              batch_size=128, show_progress_bar=True)
    index = faiss.IndexFlatIP(embeddings.shape[1])
    faiss.normalize_L2(embeddings)
    index.add(embeddings)
    faiss.write_index(index, str(INDEX_PATH))
    np.save(EMBEDDINGS_PATH, embeddings)

    # Extract poses for every clip; ~1 fps wall clock per clip is fine
    # because this is offline.
    for clip in tqdm(manifest):
        out = POSES_DIR / f"{clip['clip_id']}.json"
        if out.exists():
            continue
        poses = extract_pose_stream(Path(clip["mp4_path"]))
        out.write_text(json.dumps([p.model_dump() for p in poses]))
```

CLI flags: `--limit N`, `--skip-poses` (rebuild only the embeddings
index), `--skip-index` (rebuild only the poses).

### 5. `src/avatar/retrieval.py`

Runtime loader + query API, consumed by Phase 5's `MotionSynthStage`:

```python
class RetrievalIndex:
    def __init__(self, name: str = "openasl"): ...
    def query(self, text: str, k: int = 5) -> list[RetrievalHit]: ...
    def load_poses(self, clip_id: str) -> list[MotionFrame]: ...

class RetrievalHit(BaseModel):
    clip_id: str
    similarity: float          # cosine, 0..1
    caption_en: str
    duration_ms: int
```

The query embeds the text once with the same sentence-transformer used
at build time. `load_poses()` reads the per-clip JSON lazily.

### 6. ASL Citizen secondary index (optional, lower priority)

Same build script with a different manifest source. The motivation:
ASL Citizen is gloss-indexed with phonological annotations, so when
the OpenASL phrase retrieval misses on a specific noun ("LIBRARY",
"PIZZA"), Phase 5 can fall back to a Citizen entry before it falls
all the way back to WLASL stitching.

Ship this as `assets/corpus/aslcitizen_*.json` mirroring the OpenASL
layout. Phase 5's retrieval chain becomes
`openasl → aslcitizen → wlasl`.

### 7. WLASL keeps its existing role — but lighter

The original Phase 4 plan's pose extraction script
(`scripts/build_pose_library.py`) is the right *fallback* path: a
per-gloss keyframe library used only when both retrieval indexes miss.
Keep the archived [`phase-4-pose-library.md`](phase-4-pose-library.md)
as the spec for this fallback path. Build it *after* the corpus
retrieval is validated — week 4 or so — and only for the ~500 most
common glosses, not all 2 000.

---

## Tests to add

`tests/test_retrieval.py`:

1. `test_index_round_trips_top1` — build a tiny in-memory index over
   3 captions, query an exact caption, assert it's top-1 with
   similarity ≈ 1.0.
2. `test_index_semantic_match` — captions `["where is the bathroom?",
   "what's for dinner", "thank you"]`; query `"i need to find the
   restroom"`; assert top-1 is the bathroom caption.
3. `test_load_poses_lazy` — assert `load_poses(id)` only touches disk
   when called, not at `__init__`.
4. `test_extractor_smoke` (skipped without mediapipe) — run
   `extract_pose_stream` on a 0.5 s test clip, assert ≥ 10 frames and
   `bone_rotations` keys are non-empty.
5. `test_vrm_retarget_quaternion_norm` — pass synthetic landmarks,
   assert every returned quaternion has magnitude in `[0.95, 1.05]`.

Don't test the corpus fetch script (network-dependent) or the full
index build (long-running).

---

## Verification

### Week-2 retrieval-quality gate (gates the whole plan)

```bash
python scripts/fetch_openasl.py --limit 500
python scripts/build_corpus_index.py --limit 500
python scripts/retrieval_eval.py tests/fixtures/retrieval_eval.json
```

`tests/fixtures/retrieval_eval.json` holds **10 hand-curated English
chunks** across yes/no Q, wh-Q, negation, topic-comment, classifier,
role-shift, time anchor, numeric, and two neutral declaratives.
`retrieval_eval.py` queries each, prints top-3 with caption text, and
shows the clip MP4 path so I can eyeball them.

**Pass criteria:** ≥ 7/10 chunks have a top-3 result that I'd describe
as "semantically on-target." If we fail this gate, do not proceed —
the corpus or the embedding model is the wrong fit, and Phase 5 cannot
fix that downstream.

### Full build (week 3–4)

```bash
python scripts/fetch_openasl.py
python scripts/build_corpus_index.py
python scripts/build_pose_library.py --limit 500   # WLASL fallback subset
ls assets/corpus/openasl/         # ~50 k mp4 clips
ls assets/corpus/openasl_poses/   # same count of pose JSONs
du -sh assets/corpus              # ~150–200 GB
```

### Deaf-consultant kickoff (week 4)

Show the consultant 5 retrieved clips for 5 prepared English chunks
(news, instructional, conversational, narrative, technical-jargon).
Capture qualitative feedback on which categories the corpus handles
well vs poorly. This shapes the retrieval threshold and corpus subset
used for the public demo.

---

## Commit hygiene

1. `feat(avatar): mediapipe pose extractor + vrm retargeter`
2. `feat(scripts): fetch_openasl.py + openasl manifest format`
3. `feat(avatar): RetrievalIndex (FAISS + sentence-transformers)`
4. `feat(scripts): build_corpus_index.py — embeddings + poses`
5. `test(avatar): retrieval index + extractor coverage`
6. `chore(corpus): commit openasl_manifest.json (no video bytes)`
7. `feat(scripts): aslcitizen secondary index` *(optional)*
8. `feat(scripts): build_pose_library.py — top-500 WLASL fallback`

---

## Hand-off notes

- **Do not commit video bytes.** Add
  `assets/corpus/openasl/` and `assets/corpus/openasl_poses/` to
  `.gitignore`. Only manifests and the FAISS index file are tracked.
- **The IK retargeter is the only research-y part.** Start with the
  direct-mapping approach (rotation aligning rest direction to
  landmark-pair direction). Use rejection sampling on per-frame jitter
  via a one-pole IIR if the output is too jittery.
- **Embed at build time, embed at query time, same model.** Pin the
  model name in `config.yaml` under a new `retrieval.embedding_model`
  key so the fingerprint can track it.
- **Failure mode for malformed clips:** mediapipe occasionally returns
  empty landmarks on dark or partially-occluded frames. Log and skip;
  don't crash the whole build.

---

## Open questions

- **OpenASL licensing.** Confirm whether the release license permits a
  hosted-demo use case (vs research-only). If it's research-only, scope
  the prototype to local-only use and start the Option D commissioned
  corpus conversation earlier.
- **Should the WLASL fallback be per-gloss or per-phrase?** v1 decision:
  per-gloss (matches the archived plan). Revisit if the fallback path
  ends up firing > 30% of the time on real videos.
- **Signer consistency.** OpenASL has many signers; the retrieved clips
  will jump between them, which is visually inconsistent. For v1,
  accept the jumpiness; for v1.1, prefer a single "house signer"
  filter at query time. Defer.
