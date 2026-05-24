"""Typed Pydantic models for the GenASL pipeline.

The pipeline carries data through five stages — fetch → translate → lookup
→ chain → plan. Each stage's input/output is a model defined here, so a
stage's shape is read off its type signature instead of mining dict keys.

The final :class:`RenderPlan` is what gets written to ``logs/render_plan_*.json``
and what the compositor consumes.

Schema 4.0 is a breaking change vs. 3.0 — all legacy-only fields from the
retired Matcher / supported-set path are gone. See the plan document for
the field-level diff.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Leaf shapes
# ---------------------------------------------------------------------------

def ms_to_timecode(ms: int) -> str:
    """Format milliseconds as ``HH:MM:SS.mmm``."""
    total_s, millis = divmod(ms, 1000)
    mins, secs = divmod(total_s, 60)
    hrs, mins = divmod(mins, 60)
    return f"{hrs:02d}:{mins:02d}:{secs:02d}.{millis:03d}"


class Timing(BaseModel):
    start_ms: int
    end_ms: int
    duration_ms: int
    start_tc: str
    end_tc: str

    @classmethod
    def from_ms(cls, start_ms: int, end_ms: int) -> "Timing":
        return cls(
            start_ms=start_ms,
            end_ms=end_ms,
            duration_ms=end_ms - start_ms,
            start_tc=ms_to_timecode(start_ms),
            end_tc=ms_to_timecode(end_ms),
        )


class WordClip(BaseModel):
    """One WLASL clip resolved from a single gloss word."""

    gloss: str
    found: bool
    word_id: str | None = None
    file_path: str | None = None   # repo-relative
    abs_path: str | None = None    # filesystem-absolute
    duration_ms: int = 0


class ChainedClip(BaseModel):
    """Output of FFmpeg concat for one segment."""

    path: str        # filesystem-absolute
    rel_path: str    # repo-relative
    duration_ms: int
    clip_count: int
    glosses: list[str]


# ---------------------------------------------------------------------------
# Intermediate stage outputs — segment lineage
# ---------------------------------------------------------------------------

class TranscriptSegment(BaseModel):
    """Output of :class:`FetchStage` — one sentence-level transcript segment."""

    segment_id: str
    start_ms: int
    end_ms: int
    text: str


class GlossSegment(TranscriptSegment):
    """Output of :class:`TranslateStage` — adds the ASL gloss sequence."""

    gloss_sequence: list[str]
    gloss_text: str


class LookedUpSegment(GlossSegment):
    """Output of :class:`LookupStage` — adds per-gloss clip resolution."""

    word_clips: list[WordClip]


class ChainedSegment(LookedUpSegment):
    """Output of :class:`ChainStage` — adds the concatenated clip (or None)."""

    chained_clip: ChainedClip | None = None


# ---------------------------------------------------------------------------
# Render plan shape (schema 4.0)
# ---------------------------------------------------------------------------

SegmentAction = Literal["ASL", "CAPTIONS", "FILTERED"]


class SegmentMatch(BaseModel):
    action: SegmentAction
    gloss_sequence: list[str] = Field(default_factory=list)
    gloss_text: str = ""
    word_coverage: float = 0.0
    found_glosses: list[str] = Field(default_factory=list)
    missing_glosses: list[str] = Field(default_factory=list)
    chained_clip_path: str | None = None
    chained_duration_ms: int | None = None
    chained_clip_count: int = 0
    # Only set when action == "FILTERED"
    reason: str | None = None


class PlanSegment(BaseModel):
    segment_id: str
    source_text: str
    timing: Timing
    match: SegmentMatch


class AslOverlayEntry(BaseModel):
    """One playable ASL overlay clip with its timing window."""

    segment_id: str
    start_ms: int
    end_ms: int
    start_tc: str
    end_tc: str
    asset_file_path: str          # repo-relative, never None on the overlay track
    asset_duration_ms: int
    score: float                  # word_coverage in [0, 1]
    gloss_sequence: list[str]
    kept: bool = True             # set False by overlap resolution


class PipelineInfo(BaseModel):
    mode: Literal["genai_gloss"] = "genai_gloss"
    provider: str
    model: str


class Summary(BaseModel):
    total_segments: int
    asl_segments: int
    captions_segments: int
    filtered_segments: int
    asl_ratio: float
    timing_overlaps: int = 0
    overlaps_resolved: int = 0


class RenderPlan(BaseModel):
    schema_version: Literal["4.0"] = "4.0"
    run_id: str
    video_id: str
    generated_at: str
    pipeline: PipelineInfo
    summary: Summary
    segments: list[PlanSegment]
    filtered_segments: list[PlanSegment] = Field(default_factory=list)
    asl_overlay_track: list[AslOverlayEntry]


# ---------------------------------------------------------------------------
# Stage I/O wrappers
# ---------------------------------------------------------------------------

class FetchInput(BaseModel):
    video_id: str


class FetchOutput(BaseModel):
    segments: list[TranscriptSegment]
    filtered: list[TranscriptSegment] = Field(default_factory=list)


class TranslateInput(BaseModel):
    segments: list[TranscriptSegment]


class TranslateOutput(BaseModel):
    segments: list[GlossSegment]
    provider: str
    model: str


class LookupInput(BaseModel):
    segments: list[GlossSegment]


class LookupOutput(BaseModel):
    segments: list[LookedUpSegment]


class ChainInput(BaseModel):
    segments: list[LookedUpSegment]


class ChainOutput(BaseModel):
    segments: list[ChainedSegment]


class PlanInput(BaseModel):
    run_id: str
    video_id: str
    provider: str
    model: str
    segments: list[ChainedSegment]
    filtered: list[TranscriptSegment] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Schema 5.0 — interpreter_avatar mode (additive; v4.0 untouched)
# ---------------------------------------------------------------------------

class WordTiming(BaseModel):
    word: str
    start_ms: int
    end_ms: int


class ProsodyFrame(BaseModel):
    """One frame of prosodic features (default stride 50 ms)."""

    t_ms: int
    f0_hz: float = 0.0        # 0 when unvoiced
    rms: float = 0.0          # 0..1 normalized
    voiced: bool = False


class EmotionLabel(BaseModel):
    start_ms: int
    end_ms: int
    label: str                # e.g. "neutral", "happy", "sad", "angry", "questioning"
    intensity: float = 0.0    # 0..1


class AudioAnalysis(BaseModel):
    """Output of AudioAnalyzeStage."""

    duration_ms: int
    asr_words: list[WordTiming]
    prosody: list[ProsodyFrame]
    emotion: list[EmotionLabel]


class InterpreterChunk(BaseModel):
    """Output of SemanticChunkStage — a coherent unit fed to the interpreter LLM."""

    chunk_id: str
    start_ms: int
    end_ms: int
    text: str
    dominant_emotion: str = "neutral"
    emotion_intensity: float = 0.0
    f0_range_hz: tuple[float, float] = (0.0, 0.0)
    rms_mean: float = 0.0
    speaking_rate_wps: float = 0.0   # words per second
    ended_with_pause: bool = False


class AslPlanSegment(BaseModel):
    """Output of InterpreterPlanStage — what the 'brain' decides for one chunk."""

    chunk_id: str
    start_ms: int
    end_ms: int
    topic_comment: list[str] = Field(default_factory=list)
    sign_sequence: list[str] = Field(default_factory=list)   # internal gloss tokens
    nmm_intent: dict[str, float] = Field(default_factory=dict)
    emphasis_signs: list[str] = Field(default_factory=list)
    role_shifts: list[dict] = Field(default_factory=list)
    notes: str = ""


class MotionFrame(BaseModel):
    """One VRM humanoid-bone pose sample. Quaternions are [x,y,z,w]."""

    t_ms: int
    bone_rotations: dict[str, list[float]] = Field(default_factory=dict)
    position: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])


class NmmFrame(BaseModel):
    """One ARKit-style face blendshape sample. Weights are 0..1."""

    t_ms: int
    blendshapes: dict[str, float] = Field(default_factory=dict)


class AvatarRenderPlan(BaseModel):
    """Final output of the interpreter_avatar pipeline (consumed by three.js)."""

    schema_version: Literal["5.0"] = "5.0"
    run_id: str
    video_id: str
    generated_at: str
    duration_ms: int
    frame_rate: int = 30
    motion: list[MotionFrame] = Field(default_factory=list)
    nmm: list[NmmFrame] = Field(default_factory=list)
    plan_segments: list[AslPlanSegment] = Field(default_factory=list)
    # Optional debug payload (analysis traces); excluded from the
    # extension response when set None to keep payload small.
    debug: dict | None = None


# Stage I/O wrappers for the avatar pipeline.

class AudioIngestInput(BaseModel):
    video_id: str


class AudioIngestOutput(BaseModel):
    audio_path: str        # repo-relative
    duration_ms: int
    sample_rate_hz: int


class AudioAnalyzeInput(BaseModel):
    audio_path: str
    duration_ms: int


class AudioAnalyzeOutput(BaseModel):
    analysis: AudioAnalysis


class SemanticChunkInput(BaseModel):
    analysis: AudioAnalysis


class SemanticChunkOutput(BaseModel):
    chunks: list[InterpreterChunk]


class InterpreterPlanInput(BaseModel):
    chunks: list[InterpreterChunk]


class InterpreterPlanOutput(BaseModel):
    segments: list[AslPlanSegment]
    provider: str
    model: str


class MotionSynthInput(BaseModel):
    segments: list[AslPlanSegment]


class MotionSynthOutput(BaseModel):
    motion: list[MotionFrame]
    nmm: list[NmmFrame]
    duration_ms: int


class AvatarTimelineInput(BaseModel):
    run_id: str
    video_id: str
    motion: list[MotionFrame]
    nmm: list[NmmFrame]
    duration_ms: int
    plan_segments: list[AslPlanSegment] = Field(default_factory=list)
    analysis: AudioAnalysis | None = None     # included in debug if present
    provider: str = ""
    model: str = ""


__all__ = [
    # helpers
    "ms_to_timecode",
    # leaves
    "Timing", "WordClip", "ChainedClip",
    # segment lineage
    "TranscriptSegment", "GlossSegment", "LookedUpSegment", "ChainedSegment",
    # render plan (v4.0 — genai_gloss mode)
    "SegmentAction", "SegmentMatch", "PlanSegment", "AslOverlayEntry",
    "PipelineInfo", "Summary", "RenderPlan",
    # stage I/O (v4.0)
    "FetchInput", "FetchOutput",
    "TranslateInput", "TranslateOutput",
    "LookupInput", "LookupOutput",
    "ChainInput", "ChainOutput",
    "PlanInput",
    # schema v5.0 — interpreter_avatar mode
    "WordTiming", "ProsodyFrame", "EmotionLabel", "AudioAnalysis",
    "InterpreterChunk", "AslPlanSegment",
    "MotionFrame", "NmmFrame", "AvatarRenderPlan",
    "AudioIngestInput", "AudioIngestOutput",
    "AudioAnalyzeInput", "AudioAnalyzeOutput",
    "SemanticChunkInput", "SemanticChunkOutput",
    "InterpreterPlanInput", "InterpreterPlanOutput",
    "MotionSynthInput", "MotionSynthOutput",
    "AvatarTimelineInput",
]
