"""Gnani provider: a CONFIGURABLE HTTP adapter.

This file deliberately does NOT hard-code any Gnani endpoint, header, field name, or language code.
Fill them in .env from the official docs (docs.gnani.ai), and record what you copied in
docs/gnani_api_notes.md. If the real API does not fit this shape (for example it is WebSocket-only),
edit this file; it is the only place Gnani is touched.
"""
from __future__ import annotations

import base64
import json
import os
import time
from typing import Any

import httpx

from .base import NotConfiguredError, Provider, ProviderError, STTResult, TTSResult


def _dig(obj: Any, path: str) -> Any:
    """Dotted-path lookup into JSON; list indices allowed (e.g. results.0.text)."""
    cur = obj
    for part in path.split("."):
        if isinstance(cur, list):
            cur = cur[int(part)]
        elif isinstance(cur, dict):
            cur = cur[part]
        else:
            raise KeyError(path)
    return cur


def _subst(obj: Any, values: dict[str, str]) -> Any:
    if isinstance(obj, str):
        for k, v in values.items():
            obj = obj.replace("{" + k + "}", v)
        return obj
    if isinstance(obj, dict):
        return {k: _subst(v, values) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_subst(v, values) for v in obj]
    return obj


def _json_env(name: str) -> dict:
    raw = os.environ.get(name, "").strip() or "{}"
    try:
        v = json.loads(raw)
    except json.JSONDecodeError as e:
        raise NotConfiguredError(f"{name} is not valid JSON: {e}") from e
    if not isinstance(v, dict):
        raise NotConfiguredError(f"{name} must be a JSON object")
    return v


class GnaniProvider(Provider):
    name = "gnani"

    def __init__(self) -> None:
        self.key = os.environ.get("GNANI_API_KEY", "").strip()
        self.lang_code = os.environ.get("GNANI_LANG_CODE", "te").strip()
        self.timeout = float(os.environ.get("GNANI_TIMEOUT_S", "20"))
        self.calls = {"stt": 0, "tts": 0}      # credit tracking (calls, not credits)

    # ------------------------------------------------------------------ helpers
    def _headers(self, auth_var: str) -> dict[str, str]:
        tmpl = os.environ.get(auth_var, "").strip()
        if not self.key or not tmpl or ":" not in tmpl:
            raise NotConfiguredError(f"Set GNANI_API_KEY and {auth_var} (format 'Header-Name: value {{key}}') "
                                     "from docs.gnani.ai, then record it in docs/gnani_api_notes.md.")
        name, value = tmpl.split(":", 1)
        return {name.strip(): value.strip().replace("{key}", self.key)}

    def _post(self, **kw) -> httpx.Response:
        last: Exception | None = None
        for attempt in range(3):
            try:
                r = httpx.post(timeout=self.timeout, **kw)
                if r.status_code >= 500:
                    raise ProviderError(f"Gnani server error {r.status_code}")
                if r.status_code >= 400:
                    raise ProviderError(f"Gnani request rejected ({r.status_code}): {r.text[:200]}")
                return r
            except (httpx.HTTPError, ProviderError) as e:
                last = e
                if isinstance(e, ProviderError) and "rejected" in str(e):
                    break                     # 4xx will not fix itself: do not burn credits retrying
                time.sleep(0.4 * (attempt + 1))
        raise ProviderError(f"Gnani call failed: {last}")

    # ------------------------------------------------------------------ STT (Prisma)
    def transcribe(self, wav_bytes: bytes, lang: str = "te", hint: str | None = None) -> STTResult:
        url = os.environ.get("GNANI_STT_URL", "").strip()
        text_path = os.environ.get("GNANI_STT_TEXT_PATH", "").strip()
        if not url or not text_path:
            raise NotConfiguredError("Set GNANI_STT_URL and GNANI_STT_TEXT_PATH from docs.gnani.ai.")
        headers = self._headers("GNANI_STT_AUTH")
        code = self.lang_code or lang
        extra = _subst(_json_env("GNANI_STT_FIELDS"), {"lang": code})
        mode = os.environ.get("GNANI_STT_MODE", "multipart").strip()
        if mode == "multipart":
            field = os.environ.get("GNANI_STT_FILE_FIELD", "file")
            r = self._post(url=url, headers=headers, data={k: str(v) for k, v in extra.items()},
                           files={field: ("audio.wav", wav_bytes, "audio/wav")})
        elif mode == "json_base64":
            field = os.environ.get("GNANI_STT_AUDIO_FIELD", "audio")
            body = {**extra, field: base64.b64encode(wav_bytes).decode()}
            r = self._post(url=url, headers=headers, json=body)
        else:
            raise NotConfiguredError("GNANI_STT_MODE must be multipart or json_base64")
        self.calls["stt"] += 1
        try:
            data = r.json()
            text = str(_dig(data, text_path))
        except (ValueError, KeyError, IndexError) as e:
            raise ProviderError("Could not read the transcript from the STT response; "
                                "check GNANI_STT_TEXT_PATH against the docs example") from e
        conf = None
        conf_path = os.environ.get("GNANI_STT_CONF_PATH", "").strip()
        if conf_path:
            try:
                conf = float(_dig(data, conf_path))
            except (ValueError, KeyError, IndexError, TypeError):
                conf = None
        return STTResult(text=text, confidence=conf, language=code, raw={})

    # ------------------------------------------------------------------ TTS (Timbre)
    def synthesize(self, text: str, lang: str = "te", voice: str | None = None) -> TTSResult:
        url = os.environ.get("GNANI_TTS_URL", "").strip()
        if not url:
            raise NotConfiguredError("Set GNANI_TTS_URL from docs.gnani.ai.")
        headers = self._headers("GNANI_TTS_AUTH")
        code = self.lang_code or lang
        voice = voice or os.environ.get("GNANI_TTS_VOICE", "")
        body = _subst(_json_env("GNANI_TTS_BODY"), {"text": text, "lang": code, "voice": voice})
        r = self._post(url=url, headers=headers, json=body)
        self.calls["tts"] += 1
        mime = os.environ.get("GNANI_TTS_MIME", "audio/wav").strip()
        if os.environ.get("GNANI_TTS_RESPONSE", "binary").strip() == "base64":
            path = os.environ.get("GNANI_TTS_AUDIO_PATH", "").strip()
            if not path:
                raise NotConfiguredError("GNANI_TTS_AUDIO_PATH is required when GNANI_TTS_RESPONSE=base64")
            try:
                return TTSResult(base64.b64decode(str(_dig(r.json(), path))), mime)
            except (ValueError, KeyError, IndexError) as e:
                raise ProviderError("Could not read audio from the TTS response; check GNANI_TTS_AUDIO_PATH") from e
        return TTSResult(r.content, mime)
