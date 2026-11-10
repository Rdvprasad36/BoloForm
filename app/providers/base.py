"""Provider interface. ALL Gnani access goes through a Provider."""
from __future__ import annotations

from dataclasses import dataclass, field


class ProviderError(RuntimeError):
    """A provider call failed (network, HTTP error, bad response)."""


class NotConfiguredError(ProviderError):
    """Gnani provider used before .env / docs/gnani_api_notes.md were filled in."""


@dataclass
class STTResult:
    text: str
    confidence: float | None = None      # None if the API does not return one
    language: str = "te"
    raw: dict = field(default_factory=dict)   # never log transcripts unless DEBUG=1


@dataclass
class TTSResult:
    audio: bytes
    mime: str = "audio/wav"


class Provider:
    name = "base"

    def transcribe(self, wav_bytes: bytes, lang: str = "te", hint: str | None = None) -> STTResult:
        raise NotImplementedError

    def synthesize(self, text: str, lang: str = "te", voice: str | None = None) -> TTSResult:
        raise NotImplementedError
