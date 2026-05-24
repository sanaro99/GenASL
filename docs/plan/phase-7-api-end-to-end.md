# Phase 7 — API + End-to-End Demo

> Replaces the `/asl/avatar` stub with the real pipeline call, polishes
> the demo, and closes the prototype.

---

## Goal

After this phase, the full happy path works:

```
User opens YouTube watch page
  → extension POSTs to /asl/avatar
  → server runs InterpreterAvatarPipeline
  → server returns AvatarRenderPlan
  → extension mounts avatar and plays in sync
```

End state: a 60–90 s test video produces a playable avatar overlay
within ~30 s on a warm cache (~3 min cold) on a typical laptop.

## Why this phase

Phases 2–6 build the pieces. Phase 7 is the integration: wire the
endpoint, add the response cache, handle errors, polish UX, and run
the end-to-end demo against the test videos so the prototype is
actually demonstrable.

## Dependencies & prerequisites

- Phases 2–5 complete (`InterpreterAvatarPipeline.run()` works).
- Phase 6 complete (extension mounts avatar from a plan JSON).

---

## Step-by-step implementation

### 1. Wire `/asl/avatar` to the pipeline

Replace the stub in `src/api/server.py`:

```python
from src.pipeline.pipeline_avatar import InterpreterAvatarPipeline
from src.pipeline.io import save_avatar_plan

_pipeline: InterpreterAvatarPipeline | None = None
_avatar_cache: dict[str, dict] = {}   # video_id -> serialised plan

def _get_pipeline():
    global _pipeline
    if _pipeline is None: _pipeline = InterpreterAvatarPipeline()
    return _pipeline

def _run_pipeline_sync(video_id: str) -> dict:
    plan = _get_pipeline().run(video_id)
    save_avatar_plan(plan)
    # Drop the debug payload before returning to the extension — it can
    # be huge (analysis traces).
    return plan.model_dump(exclude={"debug"})

@app.post("/asl/avatar")
async def asl_avatar(req: AvatarRequest):
    vid = req.video_id.strip()
    if not _VIDEO_ID_RE.match(vid):
        return JSONResponse({"error": "invalid video_id"}, status_code=400)

    if vid in _avatar_cache:
        return JSONResponse(_avatar_cache[vid] | {"cached": True})

    loop = asyncio.get_event_loop()
    try:
        data = await loop.run_in_executor(None, _run_pipeline_sync, vid)
    except Exception as exc:
        logger.exception("avatar pipeline failed for %s", vid)
        return JSONResponse(
            {"error": "pipeline failed", "detail": str(exc)},
            status_code=500,
        )
    _avatar_cache[vid] = data
    cache_max = get_settings().api.response_cache_max
    if len(_avatar_cache) > cache_max:
        # Evict oldest 25% — not LRU, but good enough for a prototype.
        for k in list(_avatar_cache.keys())[: cache_max // 4]:
            del _avatar_cache[k]
    return JSONResponse(data | {"cached": False})
```

### 2. Flip the `/health` `ready` flag to `True`

Update the health endpoint to introspect the pipeline:

```python
@app.get("/health")
async def health():
    s = get_settings()
    return {
        "status": "ok",
        "time": time.time(),
        "version": "5.0.0",
        "pipeline": "interpreter_avatar",
        "vrm_model_url": s.avatar.vrm_model_url,
        "ready": True,   # all phases shipped
        "asr_model": s.audio.asr_model,
        "llm_provider": s.llm.provider,
        "cache_size": len(_avatar_cache),
    }
```

### 3. Add a CLI prewarm command

For the demo, you don't want the first user request to take 3 minutes.
Add a CLI helper:

```bash
python -m src.pipeline.run_pipeline 31y2Bq1RYQA   # already exists
python -m src.pipeline.run_pipeline I_tRSrPru94
python -m src.pipeline.run_pipeline on_1sS6Ii8M
```

Now the on-disk stage caches are warm. The response_cache loads on first
HTTP request and returns within ~1 s thereafter.

### 4. Update `/health` consumer in `popup.js`

`popup.js` already reads `body.ready`. When it's `True`, change the
status text from "API up but pipeline not fully wired" to "API ready".
(Already handled by the existing popup.js.)

### 5. README + demo doc updates

- Update the `README.md` Quickstart to remove "503 returned" caveats.
- Add a short `docs/demo.md` with: prerequisites, exact commands to run,
  test videos to use, what to expect on first run vs cached run, common
  failure modes.

### 6. Output-quality iteration loop

The first end-to-end run will produce obviously imperfect output. Spend
the bulk of Phase 7 iterating:

| Symptom | Likely cause | Where to tune |
|---------|--------------|---------------|
| Wrong words signed | ASR errors on hard accent / music | `audio.asr_model` → `medium` |
| Choppy transitions between signs | Spline window too short | `avatar.transition_ms` (try 200) |
| Avatar over-signs (too many signs per chunk) | Interpreter LLM is dumping every word as gloss | Prompt iteration: emphasise "topic-comment, not word-for-word" |
| NMMs always neutral | Interpreter never emits `nmm_intent > 0` | Add few-shots with explicit NMM intent in `interpreter/prompt.py` |
| Missing signs (skipped silently) | Pose library coverage gap | Document, do not crash. Phase 4 expansion is post-prototype work. |
| Avatar drifts from video | Frame-cursor logic in `avatar.js` | Re-check binary search; ensure cursor resets on `seeked` |

Run each test video, take notes, iterate. Track measurable success
criteria below.

---

## Verification

### Automated

```bash
pytest tests/ -v
# Add a tests/test_api_avatar.py with:
# - GET /health returns ready=true
# - POST /asl/avatar with valid id returns 200 with motion/nmm arrays
# - POST /asl/avatar with invalid id returns 400
# - second POST returns cached=true (use a FakeProvider monkey-patch)
```

### Manual end-to-end

Run on each of the four test videos in `config.yaml`:

1. Cold first run: `time curl -X POST http://127.0.0.1:8794/asl/avatar -H "Content-Type: application/json" -d '{"video_id":"<ID>"}' -o /dev/null -s -w "%{http_code} %{time_total}s\n"`
2. Warm second run: same command, expect `< 1.0s` and `cached=true`.
3. Open the YouTube page with the extension loaded. Confirm avatar
   appears, plays, pauses, seeks, rate-changes correctly (the 12-step
   manual checklist from Phase 6).

### Success criteria for "prototype complete"

- ✅ At least 3 of the 4 test videos produce a watchable avatar overlay.
- ✅ Cold-cache run < 5 min on a modern laptop (no GPU).
- ✅ Warm-cache run < 2 s end to end.
- ✅ No uncaught exceptions in the server log during a normal session.
- ✅ Plan JSON files are diff-clean reruns (deterministic fingerprints work).
- ✅ Extension mounts and tears down cleanly across SPA navigation.

A separate "production-readiness" gate (Deaf community review, corpus
expansion, on-prem option, SOC 2) is **explicitly out of scope** — see
`business/feasibility-study/05-feasibility-verdict.md`.

---

## Commit hygiene

1. `feat(api): wire /asl/avatar to InterpreterAvatarPipeline`
2. `feat(api): response cache + /health introspection`
3. `docs(demo): demo.md walkthrough + updated README quickstart`
4. `test(api): end-to-end tests with FakeProvider`
5. `chore(prompt): iterate interpreter prompt against test videos`
   (one commit per material prompt revision; bump `PROMPT_VERSION`)
6. `chore(release): tag v5.0.0-prototype`

---

## Hand-off notes

- **Don't ship the debug payload to the extension.** `model_dump(exclude={"debug"})`
  is critical — the debug field can be megabytes of prosody + analysis
  traces and slows the client-side parse.
- **Cache eviction is naive.** Good enough for a prototype; for
  production-grade, swap in `cachetools.LRUCache`.
- **Concurrent users.** The single `ThreadPoolExecutor` default of
  `min(32, cpu_count+4)` is fine for demo traffic. Don't over-engineer.
- **Server warmup.** Lifespan startup could pre-warm the Whisper model
  with a 1-second dummy audio to shave 5 s off the first request. Add
  if demo latency complaints surface.

---

## Open questions

- Should `/asl/avatar` accept query params like `?frame_rate=24`? v1
  decision: no — config-only. Re-eval after demo.
- Live status / progress streaming via SSE? v1 decision: no — the demo
  just needs a final JSON. SSE is post-prototype work.
- Should we add a CLI `--no-cache` switch on `run_pipeline.py`? Yes,
  trivial — `--use-cache=false` already supported via the function arg;
  add a flag.
