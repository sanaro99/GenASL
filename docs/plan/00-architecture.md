# 00 — Architecture (Quick Index)

> Treat this as a one-page map. The full reference lives in
> [`../architecture-overview.md`](../architecture-overview.md).

---

## The six stages

```
[1] AudioIngestStage         download video, rip 16k mono WAV
                                    │
[2] AudioAnalyzeStage        Whisper + librosa + emotion (parallel)
                                    │
[3] SemanticChunkStage       VAD + clause boundaries → InterpreterChunk[]
                                    │
[4] InterpreterPlanStage     LLM persona → AslPlanSegment[]  (the "brain")
                                    │
[5] MotionSynthStage         retrieve poses + spline + NMM-from-prosody
                                    │
[6] AvatarTimelineStage      bundle → AvatarRenderPlan v5.0
                                    │
                          (JSON sent to extension; three.js plays)
```

Every stage subclasses `Stage[InT, OutT]` from `src/pipeline/stages/base.py` and
caches its output to disk by a fingerprint of (input + relevant settings).

---

## Phase ↔ stage map

| Phase | Builds | Consumes from |
|-------|--------|---------------|
| 1 — Bootstrap | Config, schema, skeleton, mode toggle | n/a — foundation |
| 2 — Audio backbone | Stages 1, 2 (`src/audio/`) | `src/audio/source_video.py` already in place |
| 3 — Interpreter brain | Stages 3, 4 (`src/interpreter/`) | `src/llm/providers/` for the LLM call |
| 4 — Pose library | `assets/pose_library/` + `scripts/build_pose_library.py` | `assets/wlasl_clips/`, `assets/word_manifest.json` |
| 5 — Motion synthesis + NMM | Stages 5, 6 (`src/avatar/`) | `assets/pose_library/`, `AudioAnalysis` prosody |
| 6 — Chrome extension VRM | `chrome-extension/avatar.js`, vendored three.js + three-vrm | `AvatarRenderPlan` schema, `/asl/avatar` endpoint |
| 7 — API + end-to-end | `/asl/avatar` real implementation, demo polish | All prior phases |

---

## Files-at-a-glance once all phases land

```
src/
├── api/server.py                      # /health, /asl/avatar (Phase 7)
├── audio/
│   ├── source_video.py                # yt-dlp source MP4 (already in repo)
│   ├── extractor.py                   # Phase 2 — MP4 → 16k mono WAV
│   ├── asr.py                         # Phase 2 — faster-whisper wrapper
│   ├── prosody.py                     # Phase 2 — librosa F0/RMS/voicing
│   ├── emotion.py                     # Phase 2 — LLM-from-text emotion
│   └── analyzer.py                    # Phase 2 — parallel fusion
├── interpreter/
│   ├── chunker.py                     # Phase 3 — VAD + clause chunking
│   ├── prompt.py                      # Phase 3 — interpreter persona prompt
│   └── planner.py                     # Phase 3 — LLM call → AslPlanSegment
├── avatar/
│   ├── pose_library.py                # Phase 5 — loader for built JSON
│   ├── pose_extractor.py              # Phase 4 — mediapipe → joint angles
│   ├── motion_synth.py                # Phase 5 — retrieve + interpolate
│   ├── nmm.py                         # Phase 5 — prosody → blendshapes
│   └── vrm_schema.py                  # Phase 5 — JSON schema docs for three.js
├── pipeline/
│   ├── models.py                      # v5.0 (Phase 1)
│   ├── pipeline_avatar.py             # orchestrator (Phase 1 skeleton; Phase 7 wires)
│   ├── run_pipeline.py                # CLI entry (Phase 1)
│   └── stages/
│       ├── base.py                    # Stage ABC (untouched)
│       ├── audio_ingest.py            # Phase 2
│       ├── audio_analyze.py           # Phase 2
│       ├── semantic_chunk.py          # Phase 3
│       ├── interpreter_plan.py        # Phase 3
│       ├── motion_synth.py            # Phase 5
│       └── avatar_timeline.py         # Phase 5
└── llm/providers/                     # already moved here in cleanup

chrome-extension/
├── content.js                         # Phase 6 mounts avatar canvas
├── avatar.js                          # Phase 6 — three.js + VRM player
├── vendor/three.min.js                # Phase 6
└── vendor/three-vrm.min.js            # Phase 6

scripts/
└── build_pose_library.py              # Phase 4

assets/
├── pose_library/<gloss>.json          # Phase 4 output
└── wlasl_clips/                       # Phase 4 input
```

---

## The single most important invariant

The user's spec, repeated here so no contributor forgets:

> **Every hand pose comes from a Deaf-signer recording.** The AI orchestrates
> known-good primitives; it never generates a sign de novo. Pure neural
> generation only fills transitions and the NMM channel.

If a phase implementation makes this invariant impossible to verify after
the fact, the phase plan is wrong; flag it before shipping.
