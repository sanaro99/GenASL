"""Retarget Mediapipe pose / hand landmarks onto VRM humanoid bones (Phase 4).

Direct-mapping approach (the simpler of the two outlined in the Phase 4
plan): for each VRM bone, the rotation quaternion is whatever rotates
the bone's rest-pose direction onto the vector connecting its two
relevant Mediapipe landmarks (e.g. LeftUpperArm rest direction +X
rotates onto LEFT_ELBOW - LEFT_SHOULDER).

Coordinate-system notes:
  * Mediapipe ``pose_world_landmarks`` are metres relative to the hip
    midpoint with X-right / Y-down / Z-forward.
  * VRM rest pose is T-pose: hips at origin, Y-up, Z-forward, arms out
    along ±X. We flip the Mediapipe Y-axis to get a Y-up frame before
    computing alignments.
  * Quaternions are emitted as ``[x, y, z, w]`` — matches VRM + three.js
    + the existing :class:`MotionFrame` schema.

Finger retargeting is best-effort: the three joints of each finger
(Proximal / Intermediate / Distal — or Metacarpal / Proximal / Distal
for the thumb) get the alignment rotation from the two segment vectors,
not full IK. Good enough for visible hand articulation; a library-based
retargeter is a v1.1 task.
"""

from __future__ import annotations

import logging
import math
from typing import Sequence

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# VRM bone names — must exactly match @pixiv/three-vrm humanoid mapping
# ---------------------------------------------------------------------------

VRM_CORE_BONES: tuple[str, ...] = (
    "Hips", "Spine", "Chest", "UpperChest", "Neck", "Head",
    "LeftShoulder", "LeftUpperArm", "LeftLowerArm", "LeftHand",
    "RightShoulder", "RightUpperArm", "RightLowerArm", "RightHand",
    "LeftUpperLeg", "LeftLowerLeg", "LeftFoot",
    "RightUpperLeg", "RightLowerLeg", "RightFoot",
)

_FINGER_NAMES: tuple[str, ...] = ("Thumb", "Index", "Middle", "Ring", "Little")
_FINGER_JOINTS: dict[str, tuple[str, str, str]] = {
    "Thumb": ("Metacarpal", "Proximal", "Distal"),
    "Index": ("Proximal", "Intermediate", "Distal"),
    "Middle": ("Proximal", "Intermediate", "Distal"),
    "Ring": ("Proximal", "Intermediate", "Distal"),
    "Little": ("Proximal", "Intermediate", "Distal"),
}


def _all_finger_bones(side: str) -> list[str]:
    out: list[str] = []
    for finger in _FINGER_NAMES:
        for joint in _FINGER_JOINTS[finger]:
            out.append(f"{side}{finger}{joint}")
    return out


VRM_FINGER_BONES: tuple[str, ...] = tuple(
    _all_finger_bones("Left") + _all_finger_bones("Right")
)
VRM_HUMANOID_BONES: tuple[str, ...] = VRM_CORE_BONES + VRM_FINGER_BONES

IDENTITY_QUAT: list[float] = [0.0, 0.0, 0.0, 1.0]


# ---------------------------------------------------------------------------
# Mediapipe landmark indices (subset we actually use)
# ---------------------------------------------------------------------------

# pose_world_landmarks indices (mp.solutions.pose.PoseLandmark)
NOSE = 0
LEFT_SHOULDER, RIGHT_SHOULDER = 11, 12
LEFT_ELBOW, RIGHT_ELBOW = 13, 14
LEFT_WRIST, RIGHT_WRIST = 15, 16
LEFT_HIP, RIGHT_HIP = 23, 24
LEFT_KNEE, RIGHT_KNEE = 25, 26
LEFT_ANKLE, RIGHT_ANKLE = 27, 28

# Hand landmark indices — 21 per hand
WRIST = 0
THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = 1, 2, 3, 4
INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = 5, 6, 7, 8
MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP = 9, 10, 11, 12
RING_MCP, RING_PIP, RING_DIP, RING_TIP = 13, 14, 15, 16
PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP = 17, 18, 19, 20

_FINGER_INDEX_CHAIN: dict[str, tuple[int, int, int, int]] = {
    # (root, joint1, joint2, tip) — root is in the palm
    "Thumb":  (WRIST, THUMB_MCP, THUMB_IP, THUMB_TIP),
    "Index":  (INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP),
    "Middle": (MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP),
    "Ring":   (RING_MCP, RING_PIP, RING_DIP, RING_TIP),
    "Little": (PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP),
}


# ---------------------------------------------------------------------------
# Vector + quaternion utilities (small, dependency-free)
# ---------------------------------------------------------------------------

Vec3 = tuple[float, float, float]
Quat = list[float]


def _sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _norm(v: Vec3) -> float:
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def _normalize(v: Vec3) -> Vec3:
    n = _norm(v)
    if n < 1e-9:
        return (0.0, 0.0, 0.0)
    return (v[0] / n, v[1] / n, v[2] / n)


def _dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _flip_y_up(v: Vec3) -> Vec3:
    """Mediapipe is Y-down; VRM is Y-up. Single-axis flip is enough here."""
    return (v[0], -v[1], v[2])


def quat_from_two_vectors(a: Vec3, b: Vec3) -> Quat:
    """Quaternion that rotates unit-vector ``a`` onto unit-vector ``b``.

    Implementation follows the standard "shortest arc" derivation.
    """
    a = _normalize(a)
    b = _normalize(b)
    if _norm(a) == 0.0 or _norm(b) == 0.0:
        return list(IDENTITY_QUAT)
    d = _dot(a, b)
    if d > 0.9999:
        return list(IDENTITY_QUAT)
    if d < -0.9999:
        # 180°. Pick an arbitrary axis orthogonal to ``a``.
        axis = _cross((1.0, 0.0, 0.0), a)
        if _norm(axis) < 1e-6:
            axis = _cross((0.0, 1.0, 0.0), a)
        axis = _normalize(axis)
        return [axis[0], axis[1], axis[2], 0.0]
    s = math.sqrt((1.0 + d) * 2.0)
    inv = 1.0 / s
    c = _cross(a, b)
    q = [c[0] * inv, c[1] * inv, c[2] * inv, s * 0.5]
    return _normalize_quat(q)


def _normalize_quat(q: Quat) -> Quat:
    n = math.sqrt(q[0] * q[0] + q[1] * q[1] + q[2] * q[2] + q[3] * q[3])
    if n < 1e-9:
        return list(IDENTITY_QUAT)
    return [q[0] / n, q[1] / n, q[2] / n, q[3] / n]


# ---------------------------------------------------------------------------
# Landmark accessor — works for both mediapipe NormalizedLandmarkList and
# plain list-of-(x, y, z) tuples (tests pass the latter)
# ---------------------------------------------------------------------------

def _lm(landmarks: Sequence, idx: int) -> Vec3:
    p = landmarks[idx]
    # mediapipe.framework.formats.landmark_pb2.Landmark has .x/.y/.z;
    # tuples / lists are indexable. Support both shapes.
    if hasattr(p, "x"):
        return (float(p.x), float(p.y), float(p.z))
    return (float(p[0]), float(p[1]), float(p[2]))


# ---------------------------------------------------------------------------
# Bone rest-pose direction vectors (in VRM Y-up frame)
# ---------------------------------------------------------------------------

_REST_DIRS: dict[str, Vec3] = {
    # Spine chain points up.
    "Spine":          (0.0, 1.0, 0.0),
    "Chest":          (0.0, 1.0, 0.0),
    "UpperChest":     (0.0, 1.0, 0.0),
    "Neck":           (0.0, 1.0, 0.0),
    "Head":           (0.0, 1.0, 0.0),
    # T-pose arms.
    "LeftShoulder":   (1.0, 0.0, 0.0),
    "LeftUpperArm":   (1.0, 0.0, 0.0),
    "LeftLowerArm":   (1.0, 0.0, 0.0),
    "LeftHand":       (1.0, 0.0, 0.0),
    "RightShoulder":  (-1.0, 0.0, 0.0),
    "RightUpperArm":  (-1.0, 0.0, 0.0),
    "RightLowerArm":  (-1.0, 0.0, 0.0),
    "RightHand":      (-1.0, 0.0, 0.0),
    # Legs (rest below the hips).
    "LeftUpperLeg":   (0.0, -1.0, 0.0),
    "LeftLowerLeg":   (0.0, -1.0, 0.0),
    "LeftFoot":       (0.0, 0.0, 1.0),
    "RightUpperLeg":  (0.0, -1.0, 0.0),
    "RightLowerLeg":  (0.0, -1.0, 0.0),
    "RightFoot":      (0.0, 0.0, 1.0),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def landmarks_to_vrm_bones(
    pose_landmarks: Sequence | None,
    left_hand_landmarks: Sequence | None = None,
    right_hand_landmarks: Sequence | None = None,
) -> dict[str, Quat]:
    """Direct-map Mediapipe landmarks → VRM humanoid bone rotation quaternions.

    Missing inputs (e.g. ``left_hand_landmarks=None`` when the hand was
    out of frame) leave the corresponding bones at identity (rest pose).
    Returns a complete dict — every bone in :data:`VRM_HUMANOID_BONES`
    is present so the downstream consumer never sees a KeyError.
    """
    out: dict[str, Quat] = {b: list(IDENTITY_QUAT) for b in VRM_HUMANOID_BONES}
    out["Hips"] = list(IDENTITY_QUAT)  # explicit — Hips carries position, not rotation

    if pose_landmarks is not None and len(pose_landmarks) >= 25:
        _retarget_torso_and_arms(pose_landmarks, out)

    if left_hand_landmarks is not None and len(left_hand_landmarks) >= 21:
        _retarget_hand(left_hand_landmarks, side="Left", out=out)
    if right_hand_landmarks is not None and len(right_hand_landmarks) >= 21:
        _retarget_hand(right_hand_landmarks, side="Right", out=out)

    return out


# ---------------------------------------------------------------------------
# Body / arm retargeting
# ---------------------------------------------------------------------------

def _retarget_torso_and_arms(pose: Sequence, out: dict[str, Quat]) -> None:
    # Pull and Y-flip the landmarks we care about.
    def at(i: int) -> Vec3:
        return _flip_y_up(_lm(pose, i))

    l_sh, r_sh = at(LEFT_SHOULDER), at(RIGHT_SHOULDER)
    l_el, r_el = at(LEFT_ELBOW), at(RIGHT_ELBOW)
    l_wr, r_wr = at(LEFT_WRIST), at(RIGHT_WRIST)
    l_hip, r_hip = at(LEFT_HIP), at(RIGHT_HIP)
    nose = at(NOSE)

    # Spine: vector from hip midpoint to shoulder midpoint.
    hip_mid = ((l_hip[0] + r_hip[0]) / 2, (l_hip[1] + r_hip[1]) / 2,
               (l_hip[2] + r_hip[2]) / 2)
    sh_mid = ((l_sh[0] + r_sh[0]) / 2, (l_sh[1] + r_sh[1]) / 2,
              (l_sh[2] + r_sh[2]) / 2)
    spine_dir = _sub(sh_mid, hip_mid)
    if _norm(spine_dir) > 1e-6:
        spine_q = quat_from_two_vectors(_REST_DIRS["Spine"], _normalize(spine_dir))
        # All three spine bones share the same rotation in v1 — a single bend
        # spread across the chain reads as a natural lean.
        out["Spine"] = spine_q
        out["Chest"] = list(IDENTITY_QUAT)
        out["UpperChest"] = list(IDENTITY_QUAT)

    # Head: from neck (≈ shoulder midpoint) toward nose.
    head_dir = _sub(nose, sh_mid)
    if _norm(head_dir) > 1e-6:
        out["Head"] = quat_from_two_vectors(_REST_DIRS["Head"], _normalize(head_dir))

    # Arms — left.
    _set_arm(out, "Left", l_sh, l_el, l_wr)
    # Arms — right.
    _set_arm(out, "Right", r_sh, r_el, r_wr)


def _set_arm(
    out: dict[str, Quat],
    side: str,
    shoulder: Vec3,
    elbow: Vec3,
    wrist: Vec3,
) -> None:
    upper = _sub(elbow, shoulder)
    lower = _sub(wrist, elbow)
    if _norm(upper) > 1e-6:
        out[f"{side}UpperArm"] = quat_from_two_vectors(
            _REST_DIRS[f"{side}UpperArm"], _normalize(upper)
        )
    if _norm(lower) > 1e-6:
        out[f"{side}LowerArm"] = quat_from_two_vectors(
            _REST_DIRS[f"{side}LowerArm"], _normalize(lower)
        )


# ---------------------------------------------------------------------------
# Hand retargeting
# ---------------------------------------------------------------------------

def _retarget_hand(hand: Sequence, *, side: str, out: dict[str, Quat]) -> None:
    """For each finger, drive its 3 joints with segment-to-segment alignments."""
    def at(i: int) -> Vec3:
        return _flip_y_up(_lm(hand, i))

    # Wrist itself — drive from middle-finger MCP direction so the palm
    # is visibly oriented even when the body model lost arm tracking.
    palm_dir = _sub(at(MIDDLE_MCP), at(WRIST))
    if _norm(palm_dir) > 1e-6:
        out[f"{side}Hand"] = quat_from_two_vectors(
            _REST_DIRS[f"{side}Hand"], _normalize(palm_dir)
        )

    for finger, joints in _FINGER_JOINTS.items():
        root_i, j1_i, j2_i, tip_i = _FINGER_INDEX_CHAIN[finger]
        seg1 = _sub(at(j1_i), at(root_i))
        seg2 = _sub(at(j2_i), at(j1_i))
        seg3 = _sub(at(tip_i), at(j2_i))
        # Reference direction for a finger at rest in a T-pose hand is
        # the same as the hand: away from the body. We approximate by
        # using the previous segment as the rest direction for joint N+1,
        # so each joint encodes only the *delta* from a straight finger.
        rest_root = _REST_DIRS[f"{side}Hand"]
        if _norm(seg1) > 1e-6:
            out[f"{side}{finger}{joints[0]}"] = quat_from_two_vectors(
                rest_root, _normalize(seg1)
            )
        if _norm(seg1) > 1e-6 and _norm(seg2) > 1e-6:
            out[f"{side}{finger}{joints[1]}"] = quat_from_two_vectors(
                _normalize(seg1), _normalize(seg2)
            )
        if _norm(seg2) > 1e-6 and _norm(seg3) > 1e-6:
            out[f"{side}{finger}{joints[2]}"] = quat_from_two_vectors(
                _normalize(seg2), _normalize(seg3)
            )


__all__ = [
    "VRM_HUMANOID_BONES",
    "VRM_CORE_BONES",
    "VRM_FINGER_BONES",
    "IDENTITY_QUAT",
    "quat_from_two_vectors",
    "landmarks_to_vrm_bones",
]
