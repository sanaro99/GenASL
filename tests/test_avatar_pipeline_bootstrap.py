"""Bootstrap smoke tests for the interpreter_avatar pipeline.

These guard the v5.0 schema, the config sections, and the pipeline
skeleton so they don't regress as later phases land. They intentionally
do NOT exercise audio, LLM, or mediapipe — those have their own tests
in Phases 2–5.
"""

from __future__ import annotations

import pytest

from src.core.config import Settings, get_settings, reset_settings
from src.pipeline.models import (
    AslPlanSegment,
    AudioAnalysis,
    AvatarRenderPlan,
    InterpreterChunk,
    MotionFrame,
    NmmFrame,
    WordTiming,
)
from src.pipeline.pipeline_avatar import InterpreterAvatarPipeline


def test_settings_load_with_avatar_sections():
    """Settings expose audio/interpreter/avatar/pipeline sections with safe defaults."""
    reset_settings()
    s = get_settings()
    assert s.audio.asr_model in {"tiny", "base", "small", "medium"}
    assert s.interpreter.max_chunk_chars > 0
    assert s.avatar.rig == "vrm"
    assert s.avatar.frame_rate > 0
    assert s.pipeline.use_disk_cache is True


def test_settings_tolerates_legacy_top_level_keys():
    """Legacy top-level keys (e.g. test_videos) must not break loading."""
    s = Settings.model_validate(
        {
            "test_videos": [{"id": "abc", "title": "x"}],
            "avatar": {"frame_rate": 60},
        }
    )
    assert s.avatar.frame_rate == 60


def test_v5_schema_round_trips():
    """All v5.1 models serialize and deserialize without losing fields."""
    plan = AvatarRenderPlan(
        run_id="rid",
        video_id="vid",
        generated_at="2026-05-23T00:00:00Z",
        duration_ms=1000,
        motion=[MotionFrame(t_ms=0, bone_rotations={"Hips": [0, 0, 0, 1]})],
        nmm=[NmmFrame(t_ms=0, blendshapes={"browInnerUp": 0.5})],
        plan_segments=[
            AslPlanSegment(
                chunk_id="c0", start_ms=0, end_ms=1000,
                sign_sequence=["HELLO", "WORLD"],
                query_text="hello world",
                retrieved_clip_id="openasl_00042",
                retrieval_similarity=0.82,
                fidelity="retrieval",
            )
        ],
    )
    payload = plan.model_dump_json()
    parsed = AvatarRenderPlan.model_validate_json(payload)
    assert parsed.schema_version == "5.1"
    assert parsed.motion[0].bone_rotations["Hips"] == [0, 0, 0, 1]
    assert parsed.plan_segments[0].sign_sequence == ["HELLO", "WORLD"]
    assert parsed.plan_segments[0].retrieved_clip_id == "openasl_00042"
    assert parsed.plan_segments[0].fidelity == "retrieval"


def test_v5_schema_back_compat_for_pre_phase5_segments():
    """A segment without the Phase-5 retrieval fields still parses."""
    seg = AslPlanSegment(
        chunk_id="c0", start_ms=0, end_ms=1000,
        sign_sequence=["HELLO"],
    )
    assert seg.retrieved_clip_id is None
    assert seg.retrieval_similarity is None
    assert seg.fidelity is None
    assert seg.query_text == ""


def test_interpreter_chunk_and_audio_analysis_models():
    analysis = AudioAnalysis(
        duration_ms=2000,
        asr_words=[WordTiming(word="hi", start_ms=100, end_ms=400)],
        prosody=[],
        emotion=[],
    )
    chunk = InterpreterChunk(
        chunk_id="c0", start_ms=0, end_ms=2000, text="hi",
        dominant_emotion="happy", emotion_intensity=0.7,
    )
    assert analysis.asr_words[0].word == "hi"
    assert chunk.dominant_emotion == "happy"


def test_skeleton_pipeline_raises_until_phases_complete():
    """The skeleton must fail loudly, not silently return an empty plan."""
    p = InterpreterAvatarPipeline()
    with pytest.raises(NotImplementedError):
        p.run("AAAAAAAAAAA")
