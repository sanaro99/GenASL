"""Stage 4 — interpreter persona prompt + few-shot examples (Phase 3).

The prompt asks the LLM to behave like an ASL interpreter and return a
strictly-shaped JSON object describing what to sign and how to inflect
it. Timing fields are filled in from the :class:`InterpreterChunk`
upstream — the LLM never sees ms boundaries.

``PROMPT_VERSION`` is part of :class:`InterpreterPlanStage`'s cache
fingerprint; bump it whenever the prompt's *intent* changes so old
cached plans get re-generated.
"""

from __future__ import annotations

import json

from src.core.config import InterpreterSettings
from src.pipeline.models import InterpreterChunk


PROMPT_VERSION = "v1"


SYSTEM_PROMPT = """You are a fluent American Sign Language (ASL) interpreter.
Given a short English utterance plus speaker emotion and prosody, you decide:

1. ASL grammar restructuring — topic / comment order, not English word order.
2. The internal gloss sequence (UPPERCASE one-token-per-sign) to drive a
   retrieval-augmented avatar. Glosses are an INTERNAL representation — the
   end user never sees them; they are only used to look up Deaf-signed
   keyframes downstream.
3. Non-manual markers (NMM): brow raise, brow furrow (eye_squint), head
   tilt, head nod, head shake, mouth open — each on a 0..1 intensity.
4. Which signs to emphasize (lengthen + amplify NMM).
5. Optional role shifts when the speaker is quoting or embodying someone.

Hard rules:
* OUTPUT EXACTLY ONE JSON OBJECT. No prose, no markdown, no ```json fences.
* Keys: topic_comment, sign_sequence, nmm_intent, emphasis_signs,
  role_shifts, notes.
* nmm_intent keys: brow_raise, head_tilt_left, head_tilt_right, head_nod,
  head_shake, mouth_open, eye_squint — all floats in [0, 1].
* Yes/no question -> brow_raise > 0.6.
* Wh-question (who/what/where/when/why/how) -> eye_squint > 0.4 and
  brow_raise > 0.3.
* Negation (not/no/never) -> head_shake > 0.5.
* Strong affirmation or emphasis -> head_nod > 0.4.
* Glosses are UPPERCASE, ASCII letters/digits/underscore only — no punctuation.
* Keep sign_sequence to ≤ 12 tokens per chunk.
* notes ≤ 1 short sentence.
"""


FEW_SHOT_EXAMPLES = [
    {
        "user": (
            'Text: "Where is the library?"\n'
            "Emotion: questioning (0.7)\n"
            "Speaking rate (wps): 1.3\n"
            "Ended with pause: true"
        ),
        "assistant": json.dumps({
            "topic_comment": ["TOPIC: LIBRARY", "COMMENT: WHERE"],
            "sign_sequence": ["LIBRARY", "WHERE"],
            "nmm_intent": {
                "brow_raise": 0.4, "head_tilt_left": 0.0,
                "head_tilt_right": 0.1, "head_nod": 0.0,
                "head_shake": 0.0, "mouth_open": 0.2, "eye_squint": 0.6,
            },
            "emphasis_signs": ["WHERE"],
            "role_shifts": [],
            "notes": "Wh-question — furrow brow, hold WHERE.",
        }),
    },
    {
        "user": (
            'Text: "Are you coming tonight?"\n'
            "Emotion: questioning (0.6)\n"
            "Speaking rate (wps): 2.1\n"
            "Ended with pause: true"
        ),
        "assistant": json.dumps({
            "topic_comment": ["TOPIC: TONIGHT", "COMMENT: YOU COME"],
            "sign_sequence": ["TONIGHT", "YOU", "COME"],
            "nmm_intent": {
                "brow_raise": 0.8, "head_tilt_left": 0.0,
                "head_tilt_right": 0.1, "head_nod": 0.0,
                "head_shake": 0.0, "mouth_open": 0.1, "eye_squint": 0.0,
            },
            "emphasis_signs": ["COME"],
            "role_shifts": [],
            "notes": "Yes/no question — brow raise held through chunk.",
        }),
    },
    {
        "user": (
            'Text: "I do not agree with that."\n'
            "Emotion: emphatic (0.7)\n"
            "Speaking rate (wps): 2.4\n"
            "Ended with pause: false"
        ),
        "assistant": json.dumps({
            "topic_comment": ["TOPIC: THAT", "COMMENT: ME NOT AGREE"],
            "sign_sequence": ["THAT", "ME", "AGREE", "NOT"],
            "nmm_intent": {
                "brow_raise": 0.1, "head_tilt_left": 0.0,
                "head_tilt_right": 0.0, "head_nod": 0.0,
                "head_shake": 0.7, "mouth_open": 0.2, "eye_squint": 0.1,
            },
            "emphasis_signs": ["NOT"],
            "role_shifts": [],
            "notes": "Negation — head shake co-occurs with NOT.",
        }),
    },
    {
        "user": (
            'Text: "This is incredibly important."\n'
            "Emotion: emphatic (0.9)\n"
            "Speaking rate (wps): 2.0\n"
            "Ended with pause: false"
        ),
        "assistant": json.dumps({
            "topic_comment": ["TOPIC: THIS", "COMMENT: IMPORTANT VERY"],
            "sign_sequence": ["THIS", "IMPORTANT", "VERY"],
            "nmm_intent": {
                "brow_raise": 0.6, "head_tilt_left": 0.0,
                "head_tilt_right": 0.0, "head_nod": 0.6,
                "head_shake": 0.0, "mouth_open": 0.4, "eye_squint": 0.0,
            },
            "emphasis_signs": ["IMPORTANT", "VERY"],
            "role_shifts": [],
            "notes": "Emphasis — lengthen IMPORTANT with brow raise + nod.",
        }),
    },
    {
        "user": (
            'Text: "The meeting starts at three."\n'
            "Emotion: neutral (0.2)\n"
            "Speaking rate (wps): 2.6\n"
            "Ended with pause: true"
        ),
        "assistant": json.dumps({
            "topic_comment": ["TOPIC: MEETING", "COMMENT: START 3"],
            "sign_sequence": ["MEETING", "START", "TIME", "3"],
            "nmm_intent": {
                "brow_raise": 0.0, "head_tilt_left": 0.0,
                "head_tilt_right": 0.0, "head_nod": 0.1,
                "head_shake": 0.0, "mouth_open": 0.1, "eye_squint": 0.0,
            },
            "emphasis_signs": [],
            "role_shifts": [],
            "notes": "Neutral declarative.",
        }),
    },
    {
        "user": (
            'Text: "She said: I will be late."\n'
            "Emotion: neutral (0.3)\n"
            "Speaking rate (wps): 2.5\n"
            "Ended with pause: true"
        ),
        "assistant": json.dumps({
            "topic_comment": ["TOPIC: SHE", "COMMENT: SAY LATE"],
            "sign_sequence": ["SHE", "SAY", "ME", "LATE"],
            "nmm_intent": {
                "brow_raise": 0.1, "head_tilt_left": 0.3,
                "head_tilt_right": 0.0, "head_nod": 0.0,
                "head_shake": 0.0, "mouth_open": 0.2, "eye_squint": 0.0,
            },
            "emphasis_signs": [],
            "role_shifts": [
                {"target": "person", "signs": ["ME", "LATE"]}
            ],
            "notes": "Role shift to the quoted speaker on the embedded clause.",
        }),
    },
]


def build_user_prompt(
    chunk: InterpreterChunk, settings: InterpreterSettings
) -> str:
    """Render the per-chunk user message fed to the LLM."""
    lines = [
        f"Text: {chunk.text!r}",
        f"Emotion: {chunk.dominant_emotion} ({chunk.emotion_intensity:.2f})",
        f"Speaking rate (wps): {chunk.speaking_rate_wps:.2f}",
        f"Ended with pause: {str(chunk.ended_with_pause).lower()}",
    ]
    if chunk.f0_range_hz != (0.0, 0.0):
        f0_lo, f0_hi = chunk.f0_range_hz
        lines.append(f"F0 range (Hz): [{f0_lo:.0f}, {f0_hi:.0f}]")
    if chunk.rms_mean > 0:
        lines.append(f"Loudness (rms_mean): {chunk.rms_mean:.3f}")
    flags = []
    if settings.include_role_shifts:
        flags.append("role_shifts:allowed")
    if settings.include_classifiers:
        flags.append("classifiers:allowed")
    if flags:
        lines.append("Flags: " + ", ".join(flags))
    lines.append("")
    lines.append("Respond with one JSON object only.")
    return "\n".join(lines)


def build_messages(
    chunk: InterpreterChunk, settings: InterpreterSettings
) -> tuple[str, str]:
    """Return (system, user) — few-shots are folded into the user message.

    The provider abstraction only accepts a single system + single user
    message, so we render the few-shots inline as ``Example N`` blocks.
    """
    blocks = ["Few-shot examples (do not echo back):"]
    for i, ex in enumerate(FEW_SHOT_EXAMPLES, start=1):
        blocks.append(f"--- Example {i} input ---\n{ex['user']}")
        blocks.append(f"--- Example {i} output ---\n{ex['assistant']}")
    blocks.append("--- Now you ---")
    blocks.append(build_user_prompt(chunk, settings))
    return SYSTEM_PROMPT, "\n".join(blocks)


__all__ = [
    "PROMPT_VERSION",
    "SYSTEM_PROMPT",
    "FEW_SHOT_EXAMPLES",
    "build_user_prompt",
    "build_messages",
]
