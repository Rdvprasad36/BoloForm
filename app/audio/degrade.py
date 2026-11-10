"""Audio degradations for phone-line mode and for the eval harness. numpy only."""
from __future__ import annotations

import numpy as np

from .wav import read_wav, write_wav

CONDITIONS = ("clean", "noise20", "noise10", "noise5", "phone")
_SNR = {"noise20": 20.0, "noise10": 10.0, "noise5": 5.0}


def _bandpass(x: np.ndarray, sr: int, lo: float, hi: float) -> np.ndarray:
    spec = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(len(x), 1.0 / sr)
    spec[(freqs < lo) | (freqs > hi)] = 0
    return np.fft.irfft(spec, n=len(x)).astype(np.float32)


def _resample(x: np.ndarray, sr_from: int, sr_to: int) -> np.ndarray:
    if sr_from == sr_to or len(x) == 0:
        return x
    n_out = int(round(len(x) * sr_to / sr_from))
    t_out = np.arange(n_out) * (sr_from / sr_to)
    return np.interp(t_out, np.arange(len(x)), x).astype(np.float32)


def _mulaw(x: np.ndarray, mu: int = 255) -> np.ndarray:
    comp = np.sign(x) * np.log1p(mu * np.abs(x)) / np.log1p(mu)
    q = np.round((comp + 1) / 2 * mu) / mu * 2 - 1           # 8-bit quantization
    return (np.sign(q) * ((1 + mu) ** np.abs(q) - 1) / mu).astype(np.float32)


def telephony(wav_bytes: bytes) -> bytes:
    """Simulate a phone call: 300-3400 Hz band, 8 kHz sampling, 8-bit mu-law."""
    x, sr = read_wav(wav_bytes)
    x = _bandpass(x, sr, 300.0, 3400.0)
    x8 = _resample(x, sr, 8000)
    x8 = _mulaw(np.clip(x8, -1, 1))
    return write_wav(_resample(x8, 8000, sr), sr)


def _noise(kind: str, n: int, rng: np.random.Generator) -> np.ndarray:
    w = rng.standard_normal(n).astype(np.float32)
    if kind == "white":
        return w
    spec = np.fft.rfft(w)                                     # pink-ish: 1/sqrt(f)
    freqs = np.fft.rfftfreq(n, 1.0)
    freqs[0] = freqs[1] if len(freqs) > 1 else 1.0
    return np.fft.irfft(spec / np.sqrt(freqs / freqs[1]), n=n).astype(np.float32)


def add_noise(wav_bytes: bytes, snr_db: float, rng: np.random.Generator, kind: str = "pink") -> bytes:
    x, sr = read_wav(wav_bytes)
    if len(x) == 0:
        return wav_bytes
    noise = _noise(kind, len(x), rng)
    p_sig = float(np.mean(x ** 2)) + 1e-12
    p_noise = float(np.mean(noise ** 2)) + 1e-12
    noise *= np.sqrt(p_sig / (p_noise * 10 ** (snr_db / 10.0)))
    return write_wav(x + noise, sr)


def apply_condition(wav_bytes: bytes, condition: str, rng: np.random.Generator) -> bytes:
    if condition == "clean":
        return wav_bytes
    if condition == "phone":
        return telephony(wav_bytes)
    if condition in _SNR:
        return add_noise(wav_bytes, _SNR[condition], rng)
    raise ValueError(f"unknown condition {condition!r}")
