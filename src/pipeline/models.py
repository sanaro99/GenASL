"""Typed Pydantic models for the GenASL ``interpreter_avatar`` pipeline.

The pipeline runs six stages — audio_ingest → audio_analyze →
semantic_chunk → interpreter_plan → motion_synth → avatar_timeline —
and each stage's input/output is a model defined here, so a stage's
shape is read off its type signature instead of mining dict keys.

The final :class:`AvatarRenderPlan` (schema v5.0) is what gets written
to ``logs/avatar_plan_<run_id>.json`` and what the Chrome extension's
three.js consumer plays.

The previous schema v4.0 (gloss / WLASL clip-stitching mode) lives in
git history; it was removed when the codebase focused on the new
architecture.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ms_to_timecode(ms: int) -> str:
    """Format milliseconds as ``HH:MM:SS.mmm``."""
    total_s, millis = divmod(ms, 1000)
    mins, secs = divmod(total_s, 60)
    hrs, mins = divmod(mins, 60)
    return f"{hrs:02d}:{mins:02d}:{secs:02d}.{millis:03d}"


# ---------------------------------------------------------------------------
# Audio analysis (Stage 2 output)
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
    """Fused output of ASR + prosody + emotion."""

    duration_ms: int
    asr_words: list[WordTiming]
    prosody: list[ProsodyFrame]
    emotion: list[EmotionLabel]


# ---------------------------------------------------------------------------
# Semantic chunk (Stage 3 output) — coherent unit fed to the interpreter LLM
# ---------------------------------------------------------------------------

class InterpreterChunk(BaseModel):
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


# ---------------------------------------------------------------------------
# Interpreter plan (Stage 4 output) — what the "brain" decides per chunk
# ---------------------------------------------------------------------------

class AslPlanSegment(BaseModel):
    chunk_id: str
    start_ms: int
    end_ms: int
    topic_comment: list[str] = Field(default_factory=list)
    sign_sequence: list[str] = Field(default_factory=list)   # internal gloss tokens
    # Phrase-level retrieval query (Phase 4/5). The interpreter brain may
    # emit this directly; if absent the synth stage falls back to text
    # composed from topic_comment.
    query_text: str = ""
    nmm_intent: dict[str, float] = Field(default_factory=dict)
    emphasis_signs: list[str] = Field(default_factory=list)
    role_shifts: list[dict] = Field(default_factory=list)
    notes: str = ""
    # Populated by MotionSynthStage in Phase 5 (added at schema v5.1):
    retrieved_clip_id: str | None = None
    retrieval_similarity: float | None = None
    fidelity: Literal["retrieval", "lexical", "stitched", "degraded"] | None = None


# ---------------------------------------------------------------------------
# Motion timeline (Stage 5 output) — what three.js plays
# ---------------------------------------------------------------------------

class MotionFrame(BaseModel):
    """One VRM humanoid-bone pose sample. Quaternions are [x,y,z,w]."""

    t_ms: int
    bone_rotations: dict[str, list[float]] = Field(default_factory=dict)
    position: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])


class NmmFrame(BaseModel):
    """One ARKit-style face blendshape sample. Weights are 0..1."""

    t_ms: int
    blendshapes: dict[str, float] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# AvatarRenderPlan v5.0 (Stage 6 output) — final deliverable
# ---------------------------------------------------------------------------

class AvatarRenderPlan(BaseModel):
    schema_version: Literal["5.1"] = "5.1"
    run_id: str
    video_id: str
    generated_at: str
    duration_ms: int
    frame_rate: int = 30
    motion: list[MotionFrame] = Field(default_factory=list)
    nmm: list[NmmFrame] = Field(default_factory=list)
    plan_segments: list[AslPlanSegment] = Field(default_factory=list)
    # Optional debug payload (analysis traces). Excluded from the
    # extension response when set to None to keep payload small.
    debug: dict | None = None


# ---------------------------------------------------------------------------
# Stage I/O wrappers
# ---------------------------------------------------------------------------

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
    # Phase 5 fills these — mirror of the input segments with retrieval
    # metadata (clip id, similarity, fidelity tier) populated. Default
    # empty so callers built against the v5.0 shape still parse.
    annotated_segments: list[AslPlanSegment] = Field(default_factory=list)


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
    # data models
    "WordTiming", "ProsodyFrame", "EmotionLabel", "AudioAnalysis",
    "InterpreterChunk", "AslPlanSegment",
    "MotionFrame", "NmmFrame", "AvatarRenderPlan",
    # stage I/O
    "AudioIngestInput", "AudioIngestOutput",
    "AudioAnalyzeInput", "AudioAnalyzeOutput",
    "SemanticChunkInput", "SemanticChunkOutput",
    "InterpreterPlanInput", "InterpreterPlanOutput",
    "MotionSynthInput", "MotionSynthOutput",
    "AvatarTimelineInput",
]
