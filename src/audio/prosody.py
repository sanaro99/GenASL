"""Stage 2 — librosa-based prosodic feature extraction.

Emits one :class:`ProsodyFrame` every ``prosody_frame_ms`` of audio.
Each frame carries F0 (Hz; 0 when unvoiced), normalized RMS energy
(0..1), and a voiced flag. librosa + soundfile are imported lazily so
the module can be imported in tests that don't actually compute prosody.
"""

from __future__ import annotations

import logging
from pathlib import Path

from src.core.config import AudioSettings, get_settings
from src.pipeline.models import ProsodyFrame

logger = logging.getLogger(__name__)


def extract_prosody(
    wav_path: Path,
    settings: AudioSettings | None = None,
) -> list[ProsodyFrame]:
    """Compute F0 + RMS + voicing per frame for ``wav_path``."""
    import librosa  # heavy import — lazy
    import numpy as np

    s = settings or get_settings().audio
    target_sr = s.sample_rate_hz
    frame_ms = s.prosody_frame_ms

    y, sr = librosa.load(str(wav_path), sr=target_sr, mono=True)
    if y.size == 0:
        return []

    hop = max(1, int(sr * frame_ms / 1000))
    frame_length = hop * 2

    # F0 via pyin — returns f0 (NaN where unvoiced) + voiced_flag.
    f0, voiced_flag, _ = librosa.pyin(
        y,
        fmin=float(librosa.note_to_hz("C2")),   # ~65 Hz
        fmax=float(librosa.note_to_hz("C7")),   # ~2093 Hz
        sr=sr,
        frame_length=frame_length,
        hop_length=hop,
    )

    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop)[0]
    rms_norm_ref = max(float(np.percentile(rms, 99)), 1e-9)
    rms_norm = np.clip(rms / rms_norm_ref, 0.0, 1.0)

    # Align lengths — pyin and rms can differ by one frame at the edges.
    n = min(len(f0), len(voiced_flag), len(rms_norm))
    frames: list[ProsodyFrame] = []
    for i in range(n):
        f0_val = float(f0[i]) if not (f0[i] is None or np.isnan(f0[i])) else 0.0
        frames.append(
            ProsodyFrame(
                t_ms=int(i * frame_ms),
                f0_hz=f0_val,
                rms=float(rms_norm[i]),
                voiced=bool(voiced_flag[i]),
            )
        )

    logger.info("Prosody produced %d frames for %s", len(frames), wav_path.name)
    return frames
