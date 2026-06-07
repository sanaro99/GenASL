"""Phase 4 — VRM retargeting unit tests.

No mediapipe / opencv needed; the retargeter consumes plain
``(x, y, z)`` tuples, which the tests synthesize directly.
"""

from __future__ import annotations

import math

import pytest

from src.avatar.vrm_retarget import (
    IDENTITY_QUAT,
    VRM_HUMANOID_BONES,
    landmarks_to_vrm_bones,
    quat_from_two_vectors,
)


def _q_norm(q):
    return math.sqrt(sum(c * c for c in q))


def test_identity_when_vectors_equal():
    assert quat_from_two_vectors((1.0, 0.0, 0.0), (1.0, 0.0, 0.0)) == IDENTITY_QUAT
    assert quat_from_two_vectors((0.0, 1.0, 0.0), (0.0, 1.0, 0.0)) == IDENTITY_QUAT


def test_quaternion_is_unit_norm_for_random_pairs():
    pairs = [
        ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
        ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
        ((0.0, 1.0, 0.0), (-1.0, 0.0, 0.5)),
        ((0.3, 0.7, 0.2), (0.1, -0.4, 0.9)),
    ]
    for a, b in pairs:
        q = quat_from_two_vectors(a, b)
        assert 0.95 <= _q_norm(q) <= 1.05, f"q={q} norm={_q_norm(q)}"


def test_quaternion_handles_180_degree_flip():
    q = quat_from_two_vectors((1.0, 0.0, 0.0), (-1.0, 0.0, 0.0))
    assert 0.95 <= _q_norm(q) <= 1.05
    # w-component should be ~0 for a 180° rotation
    assert abs(q[3]) < 0.1


def test_landmarks_to_vrm_returns_all_bones_at_identity_without_input():
    """No landmarks → every bone present at identity, no KeyError downstream."""
    out = landmarks_to_vrm_bones(None, None, None)
    for bone in VRM_HUMANOID_BONES:
        assert bone in out
        q = out[bone]
        assert len(q) == 4
        assert 0.95 <= _q_norm(q) <= 1.05


def _make_tpose_landmarks():
    """33 landmarks in mediapipe pose-world convention (Y-down, metres)."""
    # Build with a simple object exposing .x/.y/.z to match mediapipe's API.
    class _LM:
        def __init__(self, x, y, z):
            self.x, self.y, self.z = x, y, z

    # T-pose: shoulders at +/- 0.2 X, elbows at +/- 0.5 X, wrists at +/- 0.8 X.
    # Y-down in mediapipe so "above hips" is negative y.
    lms = [_LM(0.0, 0.0, 0.0)] * 33
    lms = list(lms)  # make mutable
    lms[0]  = _LM(0.0, -0.6, 0.05)   # NOSE (above sh_mid)
    lms[11] = _LM( 0.2, -0.4, 0.0)   # LEFT_SHOULDER  (subject's left)
    lms[12] = _LM(-0.2, -0.4, 0.0)   # RIGHT_SHOULDER
    lms[13] = _LM( 0.5, -0.4, 0.0)   # LEFT_ELBOW   (extended out)
    lms[14] = _LM(-0.5, -0.4, 0.0)   # RIGHT_ELBOW
    lms[15] = _LM( 0.8, -0.4, 0.0)   # LEFT_WRIST
    lms[16] = _LM(-0.8, -0.4, 0.0)   # RIGHT_WRIST
    lms[23] = _LM( 0.1, 0.0, 0.0)    # LEFT_HIP
    lms[24] = _LM(-0.1, 0.0, 0.0)    # RIGHT_HIP
    return lms


def test_tpose_input_produces_near_identity_arm_rotations():
    """A T-pose input should give near-identity upper/lower arm quats."""
    lms = _make_tpose_landmarks()
    out = landmarks_to_vrm_bones(lms, None, None)
    # The +X arm rest direction matches the elbow-from-shoulder direction.
    for bone in ("LeftUpperArm", "RightUpperArm",
                 "LeftLowerArm", "RightLowerArm"):
        q = out[bone]
        assert 0.95 <= _q_norm(q) <= 1.05
        # |w| close to 1 for an identity-ish rotation
        assert abs(q[3]) > 0.95, f"{bone} not near identity: {q}"


def test_bent_arm_produces_non_identity_lower_arm():
    """Bend the left elbow forward; LeftLowerArm should drift from identity."""
    class _LM:
        def __init__(self, x, y, z):
            self.x, self.y, self.z = x, y, z

    lms = _make_tpose_landmarks()
    # Bend the left wrist forward in Z so the lower arm vector is no longer +X.
    lms[15] = _LM(0.5, -0.4, 0.3)  # LEFT_WRIST moved forward
    out = landmarks_to_vrm_bones(lms, None, None)
    q = out["LeftLowerArm"]
    assert abs(q[3]) < 0.99, f"expected non-identity lower-arm quat, got {q}"
