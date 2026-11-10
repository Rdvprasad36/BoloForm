"""Minimal WAV helpers (16-bit PCM). numpy + stdlib only."""
from __future__ import annotations

import io
import wave

import numpy as np


def read_wav(data: bytes) -> tuple[np.ndarray, int]:
    """Return (mono float32 samples in [-1, 1], sample_rate). Raises ValueError if not 16-bit PCM WAV."""
    try:
        with wave.open(io.BytesIO(data), "rb") as w:
            ch, width, sr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
            raw = w.readframes(n)
    except (wave.Error, EOFError) as e:
        raise ValueError(f"not a valid WAV file: {e}") from e
    if width != 2:
        raise ValueError("only 16-bit PCM WAV is supported")
    x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    return x, sr


def write_wav(x: np.ndarray, sr: int) -> bytes:
    pcm = (np.clip(x, -1.0, 1.0) * 32767.0).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()
