"""Mediapipe Holistic → VRM-rig MotionFrame stream (Phase 4).

Reads a video clip, samples it at a target FPS, runs Mediapipe Holistic
on each sampled frame, and retargets the resulting landmarks onto VRM
humanoid bones via :mod:`src.avatar.vrm_retarget`. Returns paired pose
+ NMM frames so the Phase 5 motion synthesiser can use the retrieved
clip's natural facial expressions when present.

Heavy deps (``cv2``, ``mediapipe``) are imported lazily so importing
this module is free for tests that don't exercise it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from src.avatar.vrm_retarget import (
    IDENTITY_QUAT,
    VRM_HUMANOID_BONES,
    landmarks_to_vrm_bones,
)
from src.pipeline.models import MotionFrame, NmmFrame

logger = logging.getLogger(__name__)


@dataclass
class PoseStream:
    """Paired pose + NMM tracks extracted from a single video clip."""

    motion: list[MotionFrame]
    nmm: list[NmmFrame]
    fps: int
    duration_ms: int


# Subset of ARKit blendshape names we drive directly from mediapipe's
# 468-point face mesh. The mapping is intentionally coarse — a learned
# face-to-blendshape model is a later phase.
_FACE_BLENDSHAPES = (
    "browInnerUp",
    "browDownLeft", "browDownRight",
    "eyeSquintLeft", "eyeSquintRight",
    "eyeBlinkLeft", "eyeBlinkRight",
    "jawOpen",
    "mouthSmileLeft", "mouthSmileRight",
    "mouthFrownLeft", "mouthFrownRight",
    "mouthFunnel", "mouthPucker",
)


def extract_pose_stream(
    clip_path: Path,
    target_fps: int = 30,
    *,
    model_complexity: int = 1,
) -> PoseStream:
    """Run Mediapipe Holistic on ``clip_path`` and return a :class:`PoseStream`.

    Raises ``RuntimeError`` if the clip can't be opened. Frames where
    Mediapipe finds no pose are emitted as rest-pose (identity quat per
    bone) rather than skipped, so the timeline stays gap-free.
    """
    import cv2  # type: ignore
    import mediapipe as mp  # type: ignore

    if not clip_path.is_file():
        raise RuntimeError(f"Clip not found: {clip_path}")

    cap = cv2.VideoCapture(str(clip_path))
    if not cap.isOpened():
        raise RuntimeError(f"OpenCV failed to open {clip_path}")
    source_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    source_total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if source_total <= 0:
        cap.release()
        raise RuntimeError(f"Clip {clip_path} reports 0 frames")
    stride = max(1, int(round(source_fps / float(target_fps))))
    sampled_count = (source_total + stride - 1) // stride
    duration_ms = int((source_total / source_fps) * 1000)

    logger.info(
        "Extracting pose from %s: source_fps=%.1f total=%d "
        "→ target_fps=%d stride=%d sampled≈%d duration=%dms",
        clip_path.name, source_fps, source_total, target_fps,
        stride, sampled_count, duration_ms,
    )

    motion: list[MotionFrame] = []
    nmm: list[NmmFrame] = []
    holistic = mp.solutions.holistic.Holistic(
        static_image_mode=False,
        model_complexity=model_complexity,
        smooth_landmarks=True,
        refine_face_landmarks=True,
        min_detection_confidence=0.4,
        min_tracking_confidence=0.4,
    )

    frame_idx = 0
    out_idx = 0
    try:
        while True:
            ok, frame_bgr = cap.read()
            if not ok:
                break
            if frame_idx % stride != 0:
                frame_idx += 1
                continue

            t_ms = int((frame_idx / source_fps) * 1000)
            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            try:
                result = holistic.process(rgb)
            except Exception as exc:
                logger.warning(
                    "Mediapipe Holistic failed on %s frame %d: %s — "
                    "emitting rest pose for that frame",
                    clip_path.name, frame_idx, exc,
                )
                result = None

            motion.append(_frame_to_motion(t_ms, result))
            nmm.append(_frame_to_nmm(t_ms, result))

            out_idx += 1
            if out_idx % 100 == 0:
                logger.debug(
                    "  %s: emitted %d frames (frame_idx=%d / %d)",
                    clip_path.name, out_idx, frame_idx, source_total,
                )

            frame_idx += 1
    finally:
        holistic.close()
        cap.release()

    logger.info(
        "Pose extraction done for %s: %d motion frames, %d nmm frames",
        clip_path.name, len(motion), len(nmm),
    )
    return PoseStream(
        motion=motion,
        nmm=nmm,
        fps=target_fps,
        duration_ms=duration_ms,
    )


# ---------------------------------------------------------------------------
# Per-frame conversion
# ---------------------------------------------------------------------------

def _frame_to_motion(t_ms: int, result) -> MotionFrame:
    pose_lms = None
    if result is not None and result.pose_world_landmarks is not None:
        pose_lms = result.pose_world_landmarks.landmark
    left_hand = None
    if result is not None and result.left_hand_landmarks is not None:
        left_hand = result.left_hand_landmarks.landmark
    right_hand = None
    if result is not None and result.right_hand_landmarks is not None:
        right_hand = result.right_hand_landmarks.landmark

    bone_rotations = landmarks_to_vrm_bones(pose_lms, left_hand, right_hand)
    # Hips position — mediapipe gives world-coord hip midpoint we can use as
    # a small translational offset. We zero it out for now so the avatar
    # stays anchored in the PiP canvas; later we may copy a fractional
    # value through for natural body sway.
    return MotionFrame(t_ms=t_ms, bone_rotations=bone_rotations,
                       position=[0.0, 0.0, 0.0])


def _frame_to_nmm(t_ms: int, result) -> NmmFrame:
    if result is None or result.face_landmarks is None:
        return NmmFrame(t_ms=t_ms, blendshapes={k: 0.0 for k in _FACE_BLENDSHAPES})

    lms = result.face_landmarks.landmark
    blendshapes = _coarse_face_blendshapes(lms)
    return NmmFrame(t_ms=t_ms, blendshapes=blendshapes)


def _coarse_face_blendshapes(face_landmarks) -> dict[str, float]:
    """Cheap geometric approximations of a few ARKit blendshapes.

    Mediapipe's FaceMesh model output already exposes a learned
    ``face_blendshapes`` track on newer model paths, but the Holistic
    pipeline doesn't surface it. This function picks landmarks that map
    onto the relevant facial regions and converts ratios into 0..1
    intensities. Good enough for the prototype; a learned head will
    replace it in v1.1.
    """
    # Face landmark indices reference Mediapipe canonical face mesh.
    LEFT_BROW_INNER, RIGHT_BROW_INNER = 105, 334
    LEFT_EYE_TOP, LEFT_EYE_BOTTOM = 159, 145
    RIGHT_EYE_TOP, RIGHT_EYE_BOTTOM = 386, 374
    UPPER_LIP, LOWER_LIP = 13, 14
    LEFT_MOUTH, RIGHT_MOUTH = 61, 291
    NOSE_TIP, CHIN = 1, 152

    def y(i: int) -> float:
        return float(face_landmarks[i].y)

    def dist(i: int, j: int) -> float:
        a = face_landmarks[i]
        b = face_landmarks[j]
        return ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5

    face_height = dist(NOSE_TIP, CHIN) or 1e-6

    mouth_open_ratio = dist(UPPER_LIP, LOWER_LIP) / face_height
    eye_l_ratio = dist(LEFT_EYE_TOP, LEFT_EYE_BOTTOM) / face_height
    eye_r_ratio = dist(RIGHT_EYE_TOP, RIGHT_EYE_BOTTOM) / face_height
    mouth_width_ratio = dist(LEFT_MOUTH, RIGHT_MOUTH) / face_height

    brow_l = max(0.0, min(1.0, (y(LEFT_BROW_INNER) - y(LEFT_EYE_TOP)) * 6.0))
    brow_r = max(0.0, min(1.0, (y(RIGHT_BROW_INNER) - y(RIGHT_EYE_TOP)) * 6.0))

    return {
        "browInnerUp": max(0.0, 1.0 - (brow_l + brow_r) * 0.5),
        "browDownLeft": brow_l,
        "browDownRight": brow_r,
        "eyeSquintLeft": max(0.0, 1.0 - eye_l_ratio * 10.0),
        "eyeSquintRight": max(0.0, 1.0 - eye_r_ratio * 10.0),
        "eyeBlinkLeft": max(0.0, 1.0 - eye_l_ratio * 12.0),
        "eyeBlinkRight": max(0.0, 1.0 - eye_r_ratio * 12.0),
        "jawOpen": max(0.0, min(1.0, mouth_open_ratio * 3.0)),
        "mouthSmileLeft": max(0.0, min(1.0, (mouth_width_ratio - 0.35) * 4.0)),
        "mouthSmileRight": max(0.0, min(1.0, (mouth_width_ratio - 0.35) * 4.0)),
        "mouthFrownLeft": 0.0,
        "mouthFrownRight": 0.0,
        "mouthFunnel": 0.0,
        "mouthPucker": 0.0,
    }


def rest_motion_frame(t_ms: int) -> MotionFrame:
    """Identity-quat rest frame for every VRM bone."""
    return MotionFrame(
        t_ms=t_ms,
        bone_rotations={b: list(IDENTITY_QUAT) for b in VRM_HUMANOID_BONES},
        position=[0.0, 0.0, 0.0],
    )


def rest_nmm_frame(t_ms: int) -> NmmFrame:
    return NmmFrame(t_ms=t_ms, blendshapes={k: 0.0 for k in _FACE_BLENDSHAPES})


__all__ = [
    "PoseStream",
    "extract_pose_stream",
    "rest_motion_frame",
    "rest_nmm_frame",
]
