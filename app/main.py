# -*- coding: utf-8 -*-
"""Bolo Form API. Run: uvicorn app.main:app --reload --port 8000"""
from __future__ import annotations

import base64
import json
import logging
import re
import threading
import time
from collections import OrderedDict
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .audio.degrade import telephony
from .config import ROOT, Settings
from .core import lexicon_te as L
from .core.dialogue import DialogueEngine, Session, SessionStore
from .core.forms import load_forms
from .core.noise_estimate import estimate_snr_db
from .providers.base import NotConfiguredError, ProviderError
from .providers.factory import get_provider

log = logging.getLogger("bolo")
logging.basicConfig(level=logging.INFO)

settings = Settings.load()
provider = get_provider(settings)
forms = load_forms(Path(__file__).parent / "forms")
store = SessionStore()
engine = DialogueEngine(settings.confirm_policy)
WEB = Path(__file__).parent / "web"

_tts_cache: "OrderedDict[str, tuple[str, str]]" = OrderedDict()
_tts_lock = threading.Lock()
_TTS_CACHE_MAX = 300

app = FastAPI(title="Bolo Form", version="1.0")


def _mask(s: str) -> str:
    return re.sub(r"\d{6,}", lambda m: "*" * len(m.group()), s)


def _speak(text: str) -> dict:
    """TTS with an in-memory cache (saves credits and latency). Never raises."""
    key = f"{provider.name}:{text}"
    with _tts_lock:
        if key in _tts_cache:
            _tts_cache.move_to_end(key)
            b64, mime = _tts_cache[key]
            return {"audio_b64": b64, "mime": mime, "voice_ok": True}
    try:
        r = provider.synthesize(text, "te")
    except (ProviderError, NotConfiguredError) as e:
        log.warning("TTS unavailable: %s", type(e).__name__)
        return {"audio_b64": None, "mime": None, "voice_ok": False}
    b64 = base64.b64encode(r.audio).decode()
    with _tts_lock:
        _tts_cache[key] = (b64, r.mime)
        while len(_tts_cache) > _TTS_CACHE_MAX:
            _tts_cache.popitem(last=False)
    return {"audio_b64": b64, "mime": r.mime, "voice_ok": True}


def _render(s: Session, turn: dict, **extra) -> JSONResponse:
    body = {**turn, "session_id": s.id, "prompt": {"text_te": turn["say_te"], "text_en": turn["say_en"],
                                                    **_speak(turn["say_te"])}, **extra}
    return JSONResponse(body)


def _session(sid: str) -> Session:
    s = store.get(sid)
    if s is None:
        raise HTTPException(404, "Session not found or expired. Please start again.")
    if s.turns > settings.max_turns_per_session:
        raise HTTPException(429, "Too many turns in this session.")
    return s


# ------------------------------------------------------------------ routes
@app.get("/health")
def health() -> dict:
    return {"ok": True, "provider": provider.name, "policy": settings.confirm_policy}


@app.get("/api/forms")
def list_forms() -> list[dict]:
    return [{"id": f.id, "title_te": f.title_te, "title_en": f.title_en, "fields": len(f.fields)}
            for f in forms.values()]


class StartBody(BaseModel):
    form_id: str = "farmer_scheme"
    telephony_sim: bool = False


@app.post("/api/sessions")
def start_session(body: StartBody) -> JSONResponse:
    form = forms.get(body.form_id)
    if form is None:
        raise HTTPException(404, "Unknown form")
    s = store.create(form, telephony=body.telephony_sim)
    turn = engine.start(s)
    return _render(s, turn, form_title_te=form.title_te, form_title_en=form.title_en,
                   telephony=s.telephony, provider=provider.name)


@app.post("/api/sessions/{sid}/turn")
def turn(sid: str, audio: UploadFile | None = File(None), text: str | None = Form(None),
         typed: str | None = Form(None), hint: str | None = Form(None),
         answer: str | None = Form(None), command: str | None = Form(None)) -> JSONResponse:
    s = _session(sid)
    if typed == "1":
        return _render(s, engine.handle_typed(s, text or ""))
    cmds = {"back": L.BACK[0][0], "skip": L.SKIP[0][0], "repeat": L.REPEAT[-1][0]}
    if command in cmds:                              # Back / Skip buttons: same path as the voice commands
        return _render(s, engine.handle_utterance(s, cmds[command]))
    if answer in ("yes", "no"):                      # Yes / No buttons on the confirm card
        return _render(s, engine.handle_utterance(s, L.YES_TE if answer == "yes" else L.NO_TE))

    wav = audio.file.read(settings.max_audio_bytes + 1) if audio is not None else b""
    if len(wav) > settings.max_audio_bytes:
        raise HTTPException(413, "Audio too large")
    if not wav and provider.name != "mock":
        raise HTTPException(400, "No audio received")

    snr = None
    if wav:
        try:
            if s.telephony:
                wav = telephony(wav)
        except ValueError:
            raise HTTPException(400, "Audio must be 16-bit PCM WAV")
        snr = estimate_snr_db(wav)

    t0 = time.perf_counter()
    try:
        stt = provider.transcribe(wav, "te", hint if provider.name == "mock" else None)
    except NotConfiguredError as e:
        raise HTTPException(503, str(e))
    except ProviderError as e:
        log.warning("STT failed: %s", type(e).__name__)
        return _render(s, engine.voice_unavailable(s))
    stt_ms = int((time.perf_counter() - t0) * 1000)

    if settings.debug:
        log.info("heard: %s", _mask(stt.text))
    result = engine.handle_utterance(s, stt.text, stt.confidence, snr)
    extra: dict = {"heard": stt.text}
    if settings.debug:
        extra["debug"] = {"stt_ms": stt_ms, "snr_db": snr, "confidence": stt.confidence}
    return _render(s, result, **extra)


class EditBody(BaseModel):
    value: str


@app.patch("/api/sessions/{sid}/fields/{key}")
def edit_field(sid: str, key: str, body: EditBody) -> JSONResponse:
    s = _session(sid)
    return _render(s, engine.edit_field(s, key, body.value))


@app.post("/api/sessions/{sid}/rerecord/{key}")
def rerecord(sid: str, key: str) -> JSONResponse:
    s = _session(sid)
    try:
        return _render(s, engine.rerecord(s, key))
    except KeyError:
        raise HTTPException(404, "Unknown field")


@app.get("/api/sessions/{sid}")
def get_session(sid: str) -> dict:
    s = _session(sid)
    return {"state": s.state, "form": engine._form_view(s), "telephony": s.telephony}


@app.post("/api/sessions/{sid}/finish")
def finish(sid: str) -> JSONResponse:
    s = _session(sid)
    return _render(s, engine.finish(s))


@app.post("/api/sessions/{sid}/summary_audio")
def summary_audio(sid: str) -> dict:
    """One TTS call that reads the whole review summary aloud."""
    s = _session(sid)
    parts = [f"{f['label_te']}: {f['value']}" for f in engine._form_view(s) if f["value"]]
    return _speak(". ".join(parts) or L.MSG["review"][0])


@app.delete("/api/sessions/{sid}")
def delete_session(sid: str) -> dict:
    return {"deleted": store.delete(sid)}


@app.get("/api/eval/latest")
def eval_latest() -> JSONResponse:
    p = ROOT / "eval" / "results" / "results.json"
    if not p.exists():
        raise HTTPException(404, "No eval results yet. Run: make eval")
    return JSONResponse(json.loads(p.read_text(encoding="utf-8")))


@app.get("/eval")
def eval_page() -> FileResponse:
    return FileResponse(WEB / "eval.html")


@app.get("/limits")
def limits_page() -> FileResponse:
    return FileResponse(WEB / "limits.html")


app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
