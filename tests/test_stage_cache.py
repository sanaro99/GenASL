"""Verify stage-level disk cache hit / miss / invalidation semantics."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from src.core.config import get_settings
from src.pipeline.stages.base import Stage, stable_hash


class _Inp(BaseModel):
    value: int
    extra: str = ""


class _Out(BaseModel):
    doubled: int


class _StubStage(Stage[_Inp, _Out]):
    name = "stub"
    output_model = _Out

    def __init__(self, settings, cache_root, key_includes_extra: bool = False):
        super().__init__(settings, cache_root)
        self.process_calls = 0
        self._key_includes_extra = key_includes_extra

    def fingerprint(self, inp: _Inp) -> str:
        parts: list = ["stub", inp.value]
        if self._key_includes_extra:
            parts.append(inp.extra)
        return stable_hash(parts)

    def process(self, inp: _Inp) -> _Out:
        self.process_calls += 1
        return _Out(doubled=inp.value * 2)


def test_stage_cache_hit_skips_process(tmp_path):
    """Second call with the same fingerprint reads from cache, does not re-run process."""
    settings = get_settings()
    stage = _StubStage(settings, cache_root=tmp_path)
    inp = _Inp(value=21)

    first = stage.run(inp)
    second = stage.run(inp)

    assert first.doubled == 42
    assert second.doubled == 42
    assert stage.process_calls == 1, "process should run exactly once on cache hit"


def test_stage_cache_miss_when_use_cache_false(tmp_path):
    """use_cache=False bypasses the cache even when a file is present."""
    settings = get_settings()
    stage = _StubStage(settings, cache_root=tmp_path)
    inp = _Inp(value=21)

    stage.run(inp)
    stage.run(inp, use_cache=False)

    assert stage.process_calls == 2


def test_different_inputs_get_different_fingerprints(tmp_path):
    """Different fingerprints produce independent cache entries."""
    settings = get_settings()
    stage = _StubStage(settings, cache_root=tmp_path)

    stage.run(_Inp(value=1))
    stage.run(_Inp(value=2))

    assert stage.process_calls == 2
    cached = list(stage.cache_dir.glob("*.json"))
    assert len(cached) == 2


def test_fingerprint_change_invalidates_cache(tmp_path):
    """When fingerprint logic widens to include a new field, the cache key changes."""
    settings = get_settings()
    narrow_stage = _StubStage(settings, cache_root=tmp_path, key_includes_extra=False)
    narrow_stage.run(_Inp(value=5, extra="a"))
    narrow_stage.run(_Inp(value=5, extra="b"))  # same fingerprint -> cache hit
    assert narrow_stage.process_calls == 1

    wide_stage = _StubStage(settings, cache_root=tmp_path, key_includes_extra=True)
    wide_stage.run(_Inp(value=5, extra="a"))
    wide_stage.run(_Inp(value=5, extra="b"))  # different fingerprints -> two misses
    assert wide_stage.process_calls == 2


def test_cached_output_roundtrips_pydantic(tmp_path):
    """Cached JSON is read back into the typed output model."""
    settings = get_settings()
    stage = _StubStage(settings, cache_root=tmp_path)

    fresh = stage.run(_Inp(value=7))
    cached = stage.run(_Inp(value=7))

    assert type(cached) is _Out
    assert cached.doubled == fresh.doubled == 14
