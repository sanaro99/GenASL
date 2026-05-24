"""Phase-1 bootstrap smoke tests for the interpreter_avatar pipeline.

These guard the mode-toggle and the v5.0 schema so they don't regress as
later phases land. They intentionally do NOT exercise audio, LLM, or
mediapipe — those have their own tests in Phases 2–5.
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


def test_default_mode_is_gloss():
    """Default pipeline mode must remain genai_gloss so the working PoC keeps running."""
    reset_settings()
    assert get_settings().pipeline.mode == "genai_gloss"


def test_settings_accepts_interpreter_avatar_mode():
    """The new mode is a valid Literal value on PipelineSettings."""
    s = Settings.model_validate({"pipeline": {"mode": "interpreter_avatar"}})
    assert s.pipeline.mode == "interpreter_avatar"


def test_settings_rejects_unknown_mode():
    with pytest.raises(Exception):
        Settings.model_validate({"pipeline": {"mode": "bogus"}})


def test_v5_schema_round_trips():
    """All v5.0 models serialize and deserialize without losing fields."""
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
            )
        ],
    )
    payload = plan.model_dump_json()
    parsed = AvatarRenderPlan.model_validate_json(payload)
    assert parsed.schema_version == "5.0"
    assert parsed.motion[0].bone_rotations["Hips"] == [0, 0, 0, 1]
    assert parsed.plan_segments[0].sign_sequence == ["HELLO", "WORLD"]


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
