"""Crude SNR estimate from frame energies. It is an ESTIMATE, label it as such."""
from __future__ import annotations

import math

import numpy as np

from ..audio.wav import read_wav


def estimate_snr_db(wav_bytes: bytes) -> float | None:
    """~90th percentile frame RMS (speech) vs ~10th percentile (noise floor). None if too short."""
    try:
        x, sr = read_wav(wav_bytes)
    except ValueError:
        return None
    frame = int(sr * 0.02)
    if frame <= 0 or len(x) < frame * 15:      # need ~0.3 s
        return None
    n = len(x) // frame
    rms = np.sqrt((x[: n * frame].reshape(n, frame) ** 2).mean(axis=1))
    speech, floor = float(np.percentile(rms, 90)), float(np.percentile(rms, 10))
    if speech <= 1e-5:
        return None
    return 20.0 * math.log10(speech / max(floor, 1e-5))
