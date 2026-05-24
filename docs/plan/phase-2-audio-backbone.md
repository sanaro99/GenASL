# Phase 2 — Audio Backbone

> Builds Stages 1 and 2 of the pipeline. After this phase, given a
> YouTube `video_id`, the pipeline produces an `AudioAnalysis` containing
> word-level ASR, prosodic features, and an emotion track.

---

## Goal

Implement `AudioIngestStage` and `AudioAnalyzeStage` plus the supporting
domain modules under `src/audio/`. End state: a `pytest` test feeds a
fixture WAV through the analyzer and asserts the shapes line up.

## Why this phase

Everything downstream depends on accurate, time-aligned text plus a
prosody envelope. ASR gives the words. Prosody (F0, RMS, voicing,
speaking rate) is what the interpreter brain uses to decide emphasis
and what the NMM channel uses for facial expression intensity.

## Dependencies & prerequisites

- Phase 1 complete (schema + skeleton in place).
- Add to `requirements.txt`:
  ```
  faster-whisper>=1.0.0
  librosa>=0.10
  soundfile>=0.12
  numpy
  ```
- FFmpeg available on PATH (already a prerequisite of the project).
- `src/audio/source_video.py` already in place (downloads source MP4
  via yt-dlp; reuse, do not rewrite).

---

## Step-by-step implementation

### 1. `src/audio/extractor.py`

Helper: given a video file path, run ffmpeg to rip the audio track to a
16 kHz mono WAV in `data/audio_cache/<video_id>.wav`. Return
`(wav_path, duration_ms, sample_rate_hz)`. Skip re-extraction if the WAV
already exists with the right metadata.

```python
def extract_audio(video_path: Path, video_id: str) -> tuple[Path, int, int]: ...
```

Pattern to follow: use `src.core.ffmpeg.find_ffmpeg()` for the binary;
use `src.core.paths.PROJECT_ROOT` + `settings.paths.audio_cache` for
the output dir.

### 2. `src/audio/asr.py`

Wrap `faster-whisper` with two-call interface:

```python
def transcribe(wav_path: Path, settings: AudioSettings) -> list[WordTiming]: ...
```

Use `model_size=settings.asr_model`, `compute_type=settings.asr_compute_type`,
`language=settings.asr_language`, `word_timestamps=True`. Lazily construct
the `WhisperModel` so importing this module is free — important for tests.

### 3. `src/audio/prosody.py`

`librosa`-based feature extractor:

```python
def extract_prosody(wav_path: Path, frame_ms: int) -> list[ProsodyFrame]: ...
```

Steps:
- `y, sr = librosa.load(wav_path, sr=settings.sample_rate_hz)`
- `hop = int(sr * frame_ms / 1000)`
- F0 via `librosa.pyin` (returns `f0` and a `voiced_flag` array)
- RMS via `librosa.feature.rms(y=y, frame_length=hop*2, hop_length=hop)` →
  normalize to 0..1 by dividing by the 99th percentile
- Build one `ProsodyFrame(t_ms, f0_hz, rms, voiced)` per hop

### 4. `src/audio/emotion.py`

LLM-from-text emotion (avoids shipping a second ~1 GB HF model on CPU):

```python
def classify_emotion(
    asr_words: list[WordTiming],
    prosody: list[ProsodyFrame],
    settings: InterpreterSettings,  # for temperature/window
    provider: LLMProvider | None = None,
) -> list[EmotionLabel]: ...
```

Strategy:
- Slice the ASR words into `emotion_window_ms` windows (with overlap = 0).
- For each window, summarise prosody (mean F0, max RMS, % voiced) and
  send one prompt to the LLM: "Given the text and these prosody summary
  numbers, return one label from {neutral, happy, sad, angry, anxious,
  questioning, emphatic} and an intensity 0..1. Reply JSON."
- Parse robustly (LLM may return code-fenced JSON).
- Default `provider` to `make_provider(get_settings())`.

For testing, allow injection of `FakeProvider` returning a canned label.

### 5. `src/audio/analyzer.py`

Fuses the three into an `AudioAnalysis`:

```python
def analyze(wav_path: Path, duration_ms: int) -> AudioAnalysis: ...
```

Run `asr.transcribe`, `prosody.extract_prosody`, and `emotion.classify_emotion`
in three threads (`concurrent.futures.ThreadPoolExecutor(max_workers=3)`).
ASR is CPU-heavy; prosody is light; emotion is network-bound — they
overlap well.

### 6. `src/pipeline/stages/audio_ingest.py`

```python
class AudioIngestStage(Stage[AudioIngestInput, AudioIngestOutput]):
    name = "audio_ingest"
    output_model = AudioIngestOutput

    def fingerprint(self, inp): return stable_hash(["audio_ingest", inp.video_id])

    def process(self, inp):
        video_path = download_source_video(inp.video_id)
        wav, dur_ms, sr = extract_audio(video_path, inp.video_id)
        return AudioIngestOutput(
            audio_path=str(wav.relative_to(PROJECT_ROOT)),
            duration_ms=dur_ms,
            sample_rate_hz=sr,
        )
```

### 7. `src/pipeline/stages/audio_analyze.py`

```python
class AudioAnalyzeStage(Stage[AudioAnalyzeInput, AudioAnalyzeOutput]):
    name = "audio_analyze"
    output_model = AudioAnalyzeOutput

    def fingerprint(self, inp):
        s = self.settings.audio
        return stable_hash([
            "audio_analyze", inp.audio_path,
            s.asr_model, s.asr_compute_type, s.asr_language,
            s.prosody_frame_ms, s.emotion_window_ms,
            self.settings.llm.provider,
        ])

    def process(self, inp):
        analysis = analyze(PROJECT_ROOT / inp.audio_path, inp.duration_ms)
        return AudioAnalyzeOutput(analysis=analysis)
```

### 8. Wire into `src/pipeline/pipeline_avatar.py`

Add `self.audio_ingest` and `self.audio_analyze` to `__init__`. `run()`
still raises `NotImplementedError` until Phase 5 — but a partial-pipeline
helper `run_audio_only(video_id)` is welcome for Phase 3 to consume.

### 9. Re-export from `src/pipeline/stages/__init__.py`

```python
from src.pipeline.stages.audio_ingest import AudioIngestStage
from src.pipeline.stages.audio_analyze import AudioAnalyzeStage
__all__ += ["AudioIngestStage", "AudioAnalyzeStage"]
```

---

## Tests to add

`tests/test_audio_analyzer.py`:

1. `test_prosody_frames_have_expected_stride` — synth a 1 s sine wave
   at 440 Hz, pass through `extract_prosody`, assert frames at the
   right `t_ms` and `f0_hz` close to 440.
2. `test_asr_returns_word_timings` — use a tiny WAV under
   `tests/fixtures/` (record a single word; commit < 50 kB) and assert
   `transcribe()` returns at least one `WordTiming` covering the audio.
   Mark `@pytest.mark.slow` and skip in CI if `faster-whisper` isn't
   installed.
3. `test_emotion_uses_provider` — pass a `FakeProvider` returning
   `'{"label":"happy","intensity":0.8}'`; assert one `EmotionLabel`
   with the right values.
4. `test_audio_ingest_stage_caches` — mock `download_source_video` and
   `extract_audio`, run the stage twice with the same `video_id`,
   assert second call hits the cache.
5. `test_audio_analyze_stage_fingerprint_includes_model` — same input
   path but different `asr_model` produces different cache keys.

Run with `pytest tests/ -q` after each step.

---

## Verification

```bash
# Unit tests
pytest tests/test_audio_analyzer.py -v

# Manual sanity (with API key set if using gemini/openai)
python - <<'EOF'
from pathlib import Path
from src.audio.analyzer import analyze
from src.core.paths import ASSETS_DIR
wav = ASSETS_DIR / "downloads" / "31y2Bq1RYQA.wav"  # extract first via extractor
a = analyze(wav, duration_ms=int(wav.stat().st_size / 32))  # approx
print(f"asr_words={len(a.asr_words)} prosody={len(a.prosody)} emotion={len(a.emotion)}")
EOF
```

Expected: `asr_words` non-empty, `prosody` ≈ duration_ms / prosody_frame_ms,
`emotion` non-empty.

---

## Commit hygiene

Suggested split:

1. `feat(audio): add ffmpeg extractor + faster-whisper ASR wrapper`
2. `feat(audio): add librosa prosody + LLM emotion classifier`
3. `feat(audio): fuse ASR + prosody + emotion into AudioAnalysis`
4. `feat(pipeline): wire AudioIngestStage + AudioAnalyzeStage`
5. `test(audio): coverage for the audio backbone`

---

## Hand-off notes

- **CPU-only with faster-whisper:** start with `asr_model="small"` and
  `compute_type="int8"`; a 60 s English clip should take 5–15 s on a
  decent laptop. If users complain, document the upgrade path to
  `medium` + `int8_float16` on GPU.
- **Long videos:** `extract_audio` should handle 60-minute videos. ASR
  on 60 minutes can take 5–10 min on CPU. Phase 7 will document this
  expectation. Keep the per-stage cache aggressive so reruns are cheap.
- **No GPU dependency creep:** do not pull in `torch` here. faster-whisper
  uses CTranslate2 which is CPU/GPU-agnostic and ships its own runtime.
- **Audio cache invalidation:** if a user re-downloads the same video,
  `extract_audio` should detect mtime change and re-extract. Use mtime
  in the fingerprint, not just the path.
- **Privacy hygiene:** the WAV files in `data/audio_cache/` are
  user-input-derived. Already gitignored by the `data/` rule via the
  cache_dir convention — verify before shipping.

---

## Open questions

- Should emotion classification ever fall back to a small HF audio model
  for offline use? Decision deferred to after Phase 7 demo feedback.
- For long videos, do we want a `max_duration_ms` guard in
  `AudioIngestStage` to refuse > 30-minute videos in the prototype?
  Recommended yes — set to 1800000 ms with a clear error.
