"""Mock provider: works offline. Used for tests, local UI development and dry runs.

NOTHING produced here reflects Gnani's real accuracy. mock_roundtrip() injects *simulated*
recognition errors so the dialogue and eval code can be exercised.
"""
from __future__ import annotations

import math
import random
import re

import numpy as np

from ..audio.wav import write_wav
from ..core import lexicon_te as L
from .base import Provider, STTResult, TTSResult

# Simulated per-utterance error probability by condition (made-up numbers, for plumbing only)
SIM_ERROR_RATE = {"clean": 0.03, "noise20": 0.06, "noise10": 0.15, "noise5": 0.30, "phone": 0.12}


class MockProvider(Provider):
    name = "mock"

    def transcribe(self, wav_bytes: bytes, lang: str = "te", hint: str | None = None) -> STTResult:
        """Returns the hint text (the UI sends what the developer typed). Real audio is ignored."""
        if hint:
            return STTResult(text=hint, confidence=None, language=lang)
        return STTResult(text="", confidence=None, language=lang)

    def synthesize(self, text: str, lang: str = "te", voice: str | None = None) -> TTSResult:
        """A short soft beep whose length depends on the text. Not speech."""
        sr = 16000
        dur = min(1.2, 0.25 + 0.01 * len(text))
        t = np.arange(int(sr * dur)) / sr
        env = np.minimum(1.0, np.minimum(t, dur - t) * 20)
        return TTSResult(write_wav((0.15 * env * np.sin(2 * math.pi * 440 * t)).astype(np.float32), sr), "audio/wav")

    # ---- used by the eval harness when running on the mock provider ----
    def mock_roundtrip(self, text: str, condition: str, rng: random.Random) -> STTResult:
        """Simulate TTS -> degrade -> STT on text only, with injected errors."""
        if rng.random() < SIM_ERROR_RATE.get(condition, 0.1):
            text = corrupt(text, rng)
        return STTResult(text=text, confidence=None)


def corrupt(text: str, rng: random.Random) -> str:
    """Simulate a recognition error: change a digit, swap a number word, or damage a word."""
    digits = [m for m in re.finditer(r"\d", text)]
    if digits:
        m = rng.choice(digits)
        new = rng.choice([c for c in "0123456789" if c != m.group()])
        return text[:m.start()] + new + text[m.end():]
    toks = text.split()
    num_idx = [i for i, t in enumerate(toks) if t in L.UNITS or t in L.TENS or t in L.TEENS]
    if num_idx:
        i = rng.choice(num_idx)
        pool = L.UNITS if toks[i] in L.UNITS else (L.TENS if toks[i] in L.TENS else L.TEENS)
        alts = [w for w, v in pool.items() if v != pool[toks[i]] and not w.isascii()]
        toks[i] = rng.choice(alts)
        return " ".join(toks)
    if toks:
        i = rng.randrange(len(toks))
        toks[i] = toks[i][: max(1, len(toks[i]) - 2)]
        return " ".join(toks)
    return text
