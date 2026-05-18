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

class Timing(BaseModel):
    start_ms: int
    end_ms: int
    duration_ms: int
    start_tc: str
    end_tc: str


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


__all__ = [
    # leaves
    "Timing", "WordClip", "ChainedClip",
    # segment lineage
    "TranscriptSegment", "GlossSegment", "LookedUpSegment", "ChainedSegment",
    # render plan
    "SegmentAction", "SegmentMatch", "PlanSegment", "AslOverlayEntry",
    "PipelineInfo", "Summary", "RenderPlan",
    # stage I/O
    "FetchInput", "FetchOutput",
    "TranslateInput", "TranslateOutput",
    "LookupInput", "LookupOutput",
    "ChainInput", "ChainOutput",
    "PlanInput",
]
