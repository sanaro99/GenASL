"""Stage 4 — interpreter brain that turns chunks into AslPlanSegments (Phase 3).

Calls the configured :class:`LLMProvider` once per :class:`InterpreterChunk`.
Robust to malformed model output: strips ``json`` fences, retries once,
then falls back to a minimal segment whose ``sign_sequence`` is the
chunk text uppercased.

The planner intentionally does NOT filter ``sign_sequence`` tokens against
the pose library — Phase 5's motion synthesiser is responsible for
skipping glosses with no matching keyframe.
"""

from __future__ import annotations

import json
import logging
import re

from src.core.config import InterpreterSettings, get_settings
from src.interpreter.prompt import build_messages
from src.llm.providers import LLMProvider, make_provider
from src.pipeline.models import AslPlanSegment, InterpreterChunk

logger = logging.getLogger(__name__)


_NMM_KEYS = (
    "brow_raise",
    "head_tilt_left",
    "head_tilt_right",
    "head_nod",
    "head_shake",
    "mouth_open",
    "eye_squint",
)

_GLOSS_OK = re.compile(r"^[A-Z0-9_]+$")
_WORD_TO_GLOSS = re.compile(r"[^A-Za-z0-9_]+")


def _strip_fences(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _extract_json_object(text: str) -> dict | None:
    """Pull the first ``{...}`` block out of ``text``; return None if invalid."""
    if not text:
        return None
    cleaned = _strip_fences(text)
    try:
        loaded = json.loads(cleaned)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not m:
            return None
        try:
            loaded = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    return loaded if isinstance(loaded, dict) else None


def _normalize_gloss(token: str) -> str | None:
    if not isinstance(token, str):
        return None
    candidate = _WORD_TO_GLOSS.sub("", token.strip().upper())
    if not candidate or not _GLOSS_OK.match(candidate):
        return None
    return candidate


def _clean_sign_list(items) -> list[str]:
    if not isinstance(items, list):
        return []
    out: list[str] = []
    for it in items:
        g = _normalize_gloss(it)
        if g is not None:
            out.append(g)
    return out


def _clean_nmm(intent) -> dict[str, float]:
    out: dict[str, float] = {}
    if not isinstance(intent, dict):
        intent = {}
    for key in _NMM_KEYS:
        raw = intent.get(key, 0.0)
        try:
            val = float(raw)
        except (TypeError, ValueError):
            val = 0.0
        out[key] = max(0.0, min(1.0, val))
    return out


def _clean_role_shifts(items) -> list[dict]:
    if not isinstance(items, list):
        return []
    out: list[dict] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        target = str(it.get("target", "")).strip().lower() or "person"
        signs = _clean_sign_list(it.get("signs", []))
        if not signs:
            continue
        out.append({"target": target, "signs": signs})
    return out


def _segment_from_dict(
    data: dict, chunk: InterpreterChunk
) -> AslPlanSegment:
    topic_comment = data.get("topic_comment", [])
    if not isinstance(topic_comment, list):
        topic_comment = []
    topic_comment = [str(x).strip() for x in topic_comment if str(x).strip()]

    notes_raw = data.get("notes", "")
    notes = str(notes_raw).strip() if notes_raw is not None else ""

    return AslPlanSegment(
        chunk_id=chunk.chunk_id,
        start_ms=chunk.start_ms,
        end_ms=chunk.end_ms,
        topic_comment=topic_comment,
        sign_sequence=_clean_sign_list(data.get("sign_sequence", []))[:12],
        nmm_intent=_clean_nmm(data.get("nmm_intent", {})),
        emphasis_signs=_clean_sign_list(data.get("emphasis_signs", [])),
        role_shifts=_clean_role_shifts(data.get("role_shifts", [])),
        notes=notes,
    )


def _fallback_segment(chunk: InterpreterChunk, reason: str) -> AslPlanSegment:
    signs = _clean_sign_list(chunk.text.split())
    return AslPlanSegment(
        chunk_id=chunk.chunk_id,
        start_ms=chunk.start_ms,
        end_ms=chunk.end_ms,
        topic_comment=[],
        sign_sequence=signs[:12],
        nmm_intent=_clean_nmm({}),
        emphasis_signs=[],
        role_shifts=[],
        notes=f"fallback: {reason}",
    )


def _plan_one(
    chunk: InterpreterChunk,
    settings: InterpreterSettings,
    provider: LLMProvider,
) -> AslPlanSegment:
    system, user = build_messages(chunk, settings)
    try:
        reply = provider.chat(system, user, max_tokens=400)
    except Exception as exc:  # network / quota / etc.
        logger.warning("Interpreter LLM call failed (%s); using fallback", exc)
        return _fallback_segment(chunk, "LLM call failed")

    parsed = _extract_json_object(reply)
    if parsed is None:
        try:
            retry = provider.chat(
                system,
                user + "\n\nReminder: respond with ONE JSON object only.",
                max_tokens=400,
            )
        except Exception as exc:
            logger.warning("Interpreter LLM retry failed (%s)", exc)
            return _fallback_segment(chunk, "LLM parse failed")
        parsed = _extract_json_object(retry)
        if parsed is None:
            return _fallback_segment(chunk, "LLM parse failed")

    return _segment_from_dict(parsed, chunk)


def plan_chunks(
    chunks: list[InterpreterChunk],
    settings: InterpreterSettings | None = None,
    provider: LLMProvider | None = None,
) -> tuple[list[AslPlanSegment], str, str]:
    """Run the interpreter brain over ``chunks``.

    Returns ``(segments, provider_name, model_name)`` so downstream stages
    (and the cache fingerprint of the final ``AvatarRenderPlan``) can
    record which LLM produced the plan.
    """
    s = settings or get_settings().interpreter
    prov = provider or make_provider()
    segments = [_plan_one(c, s, prov) for c in chunks]
    logger.info(
        "Planner produced %d segments via provider=%s model=%s",
        len(segments), prov.name, prov.model,
    )
    return segments, prov.name, prov.model
