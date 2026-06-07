"""Phase 4 — WLASL pose library loader tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.avatar.pose_library import PoseLibrary, PoseLibraryEntry
from src.pipeline.models import MotionFrame, NmmFrame


def _write_entry(root: Path, gloss: str, n_frames: int = 3) -> None:
    root.mkdir(parents=True, exist_ok=True)
    entry = PoseLibraryEntry(
        gloss=gloss,
        duration_ms=n_frames * 33,
        fps=30,
        source_clip=f"assets/words/{gloss}.mp4",
        keyframes=[
            MotionFrame(t_ms=i * 33,
                        bone_rotations={"Hips": [0.0, 0.0, 0.0, 1.0]})
            for i in range(n_frames)
        ],
        nmm=[
            NmmFrame(t_ms=i * 33, blendshapes={"jawOpen": 0.1 * i})
            for i in range(n_frames)
        ],
    )
    (root / f"{gloss}.json").write_text(entry.model_dump_json(), encoding="utf-8")


def test_loads_known_gloss(tmp_path):
    _write_entry(tmp_path, "HELLO", n_frames=5)
    lib = PoseLibrary(root=tmp_path)

    assert lib.has("HELLO")
    entry = lib.get("HELLO")
    assert entry.gloss == "HELLO"
    assert len(entry.keyframes) == 5
    assert entry.keyframes[0].bone_rotations["Hips"] == [0.0, 0.0, 0.0, 1.0]


def test_missing_gloss(tmp_path):
    lib = PoseLibrary(root=tmp_path)
    assert lib.has("XYZZY") is False
    with pytest.raises(KeyError):
        lib.get("XYZZY")


def test_lookup_is_case_insensitive(tmp_path):
    _write_entry(tmp_path, "LIBRARY")
    lib = PoseLibrary(root=tmp_path)
    assert lib.has("library")
    assert lib.get("library").gloss == "LIBRARY"


def test_glosses_property(tmp_path):
    _write_entry(tmp_path, "HELLO")
    _write_entry(tmp_path, "WORLD")
    lib = PoseLibrary(root=tmp_path)
    assert lib.glosses == {"HELLO", "WORLD"}


def test_get_is_cached(tmp_path):
    _write_entry(tmp_path, "HELLO")
    lib = PoseLibrary(root=tmp_path)
    first = lib.get("HELLO")
    # Mutate the file on disk; the cached value must be returned unchanged.
    (tmp_path / "HELLO.json").write_text("not even json", encoding="utf-8")
    second = lib.get("HELLO")
    assert first is second


def test_lazy_no_disk_touch_at_init(tmp_path):
    """Constructor must not read any files — only has()/get()/glosses do."""
    # Create the library, then add a file. has() should see it.
    lib = PoseLibrary(root=tmp_path)
    assert lib.glosses == set()
    _write_entry(tmp_path, "LATER")
    assert lib.has("LATER")
