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

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .audio.degrade import telephony
from .config import ROOT, Settings
from .core import lexicon_te as L
from .core.dialogue import DialogueEngine, Session, SessionStore
from .core.forms import load_forms
from .core.noise_estimate import estimate_snr_db
from .core.submissions import SubmissionFieldValue, SubmissionStore
from .core.tenants import TenantDef, load_tenants
from .providers.base import NotConfiguredError, ProviderError
from .providers.factory import get_provider

log = logging.getLogger("bolo")
logging.basicConfig(level=logging.INFO)

settings = Settings.load()
provider = get_provider(settings)
forms = load_forms(Path(__file__).parent / "forms")
tenants = load_tenants(ROOT / "tenants")
store = SessionStore()
submissions = SubmissionStore()
engine = DialogueEngine(settings.confirm_policy)
WEB = Path(__file__).parent / "web"

_tts_cache: "OrderedDict[str, tuple[str, str]]" = OrderedDict()
_tts_lock = threading.Lock()
_TTS_CACHE_MAX = 300

# Per-IP rate limiting
_ip_records: dict[str, list[float]] = {}
_ip_lock = threading.Lock()

app = FastAPI(title="Bolo Form", version="1.0")


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith("/widget") or request.url.path == "/embed.js":
        response.headers["Content-Security-Policy"] = "frame-ancestors *"
    else:
        response.headers["Permissions-Policy"] = "microphone=(self)"
    return response


def _check_rate_limit(request: Request) -> None:
    client_ip = request.client.host if request.client else "unknown"
    if client_ip == "testclient":
        return
    now = time.time()
    cutoff = now - settings.rate_limit_window_s
    with _ip_lock:
        timestamps = _ip_records.get(client_ip, [])
        timestamps = [t for t in timestamps if t > cutoff]
        if len(timestamps) >= settings.rate_limit_per_ip:
            raise HTTPException(429, "Rate limit reached. Please wait a few moments or switch to typing.")
        timestamps.append(now)
        _ip_records[client_ip] = timestamps


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
        r = provider.synthesize(text, "te-IN" if provider.name == "gnani" else "te")
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


def _get_tenant(key_or_id: str) -> TenantDef | None:
    for t in tenants.values():
        if t.public_key == key_or_id or t.id == key_or_id:
            return t
    return None


# ------------------------------------------------------------------ routes
@app.get("/health")
def health() -> dict:
    res = {"ok": True, "provider": provider.name, "policy": settings.confirm_policy}
    if hasattr(provider, "calls"):
        res["calls"] = dict(provider.calls)
    return res


@app.get("/api/forms")
def list_forms() -> list[dict]:
    return [{"id": f.id, "title_te": f.title_te, "title_en": f.title_en, "fields": len(f.fields)}
            for f in forms.values()]


class StartBody(BaseModel):
    form_id: str = "farmer_scheme"
    telephony_sim: bool = False
    public_key: str | None = None
    demo_code: str | None = None


@app.post("/api/sessions")
def start_session(body: StartBody) -> JSONResponse:
    form = forms.get(body.form_id)
    if form is None:
        raise HTTPException(404, "Unknown form")

    tenant_id = None
    if body.public_key:
        tenant = _get_tenant(body.public_key)
        if tenant:
            tenant_id = tenant.id

    demo_ok = False
    if not settings.demo_code or (body.demo_code and body.demo_code.strip() == settings.demo_code):
        demo_ok = True

    s = store.create(form, telephony=body.telephony_sim, tenant_id=tenant_id, demo_code_ok=demo_ok)
    turn = engine.start(s)
    return _render(s, turn, form_title_te=form.title_te, form_title_en=form.title_en,
                   telephony=s.telephony, provider=provider.name)


@app.post("/api/sessions/{sid}/turn")
def turn(sid: str, request: Request, audio: UploadFile | None = File(None), text: str | None = Form(None),
         typed: str | None = Form(None), hint: str | None = Form(None),
         answer: str | None = Form(None), command: str | None = Form(None),
         demo_code: str | None = Form(None)) -> JSONResponse:
    _check_rate_limit(request)
    s = _session(sid)

    if typed == "1":
        return _render(s, engine.handle_typed(s, text or ""))
    cmds = {"back": L.BACK[0][0], "skip": L.SKIP[0][0], "repeat": L.REPEAT[-1][0]}
    if command in cmds:
        return _render(s, engine.handle_utterance(s, cmds[command]))
    if answer in ("yes", "no"):
        return _render(s, engine.handle_utterance(s, L.YES_TE if answer == "yes" else L.NO_TE))

    wav = audio.file.read(settings.max_audio_bytes + 1) if audio is not None else b""
    if len(wav) > settings.max_audio_bytes:
        raise HTTPException(413, "Audio too large")
    if not wav and provider.name != "mock":
        raise HTTPException(400, "No audio received")

    # Protection for live Gnani calls
    if provider.name == "gnani":
        # Check demo code
        code_provided = demo_code or request.headers.get("X-Demo-Code")
        if settings.demo_code and not s.demo_code_ok:
            if code_provided and code_provided.strip() == settings.demo_code:
                s.demo_code_ok = True
            else:
                return _render(s, engine.voice_unavailable(s),
                               notice="Live voice requires a demo code. Falling back to typing.")

        # Check call budget cap
        total_live_calls = getattr(provider, "calls", {}).get("stt", 0) + getattr(provider, "calls", {}).get("tts", 0)
        if total_live_calls >= settings.max_live_calls_per_day:
            log.warning("Daily live call limit reached (%d calls)", total_live_calls)
            return _render(s, engine.voice_unavailable(s),
                           notice="Daily voice budget cap reached. Please type your answer.")

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
        stt = provider.transcribe(wav, "te-IN" if provider.name == "gnani" else "te",
                                  hint if provider.name == "mock" else None)
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


@app.post("/api/sessions/{sid}/submit")
def submit_session(sid: str, key: str | None = None) -> dict:
    s = _session(sid)
    tenant_id = s.tenant_id or "demo_company"
    if key:
        t = _get_tenant(key)
        if t:
            tenant_id = t.id

    t_def = tenants.get(tenant_id)
    company_lang = t_def.company_language if t_def else "en"

    values = {}
    for f in s.form.fields:
        st = s.fields[f.key]
        if st.status != "empty":
            display_comp = st.display_en if st.display_en else str(st.value if st.value is not None else "")
            trans_by = "label" if f.type == "choice" else "neutral"
            values[f.key] = SubmissionFieldValue(
                value=st.value,
                display_user=st.display,
                display_company=display_comp,
                status=st.status,
                source=st.source or "voice",
                translated_by=trans_by,
            )

    sub = submissions.create(
        tenant_id=tenant_id,
        form_id=s.form.id,
        user_language="te",
        company_language=company_lang,
        values=values,
    )
    return {
        "ok": True,
        "submission_id": sub.id,
        "delete_token": sub.delete_token,
        "created_at": sub.created_at,
        "expires_at": sub.expires_at,
    }


@app.delete("/api/submissions/{sub_id}")
def delete_submission(sub_id: str, request: Request, token: str | None = None) -> dict:
    auth_header = request.headers.get("Authorization", "")
    t = token or (auth_header[7:].strip() if auth_header.startswith("Bearer ") else "")
    if not t:
        raise HTTPException(401, "Token required to delete submission")
    if not submissions.delete(sub_id, t):
        raise HTTPException(404, "Submission not found or invalid delete token")
    return {"deleted": True, "id": sub_id}


def _verify_tenant_admin(tenant_id: str, request: Request, token: str | None = None) -> TenantDef:
    t = tenants.get(tenant_id)
    if not t:
        raise HTTPException(404, f"Tenant {tenant_id!r} not found")
    auth_header = request.headers.get("Authorization", "")
    supplied = token or (auth_header[7:].strip() if auth_header.startswith("Bearer ") else "")
    expected = t.get_admin_token()
    if not supplied or supplied != expected:
        raise HTTPException(401, "Invalid tenant admin token")
    return t


@app.get("/api/inbox.json")
def inbox_json(request: Request, tenant: str = "demo_company", token: str | None = None) -> list[dict]:
    t = _verify_tenant_admin(tenant, request, token)
    subs = submissions.list_for_tenant(t.id)
    return [
        {
            "id": s.id,
            "tenant_id": s.tenant_id,
            "form_id": s.form_id,
            "user_language": s.user_language,
            "company_language": s.company_language,
            "created_at": s.created_at,
            "expires_at": s.expires_at,
            "values": s.values,
        }
        for s in subs
    ]


@app.get("/api/inbox.csv")
def inbox_csv(request: Request, tenant: str = "demo_company", token: str | None = None) -> Response:
    t = _verify_tenant_admin(tenant, request, token)
    csv_data = submissions.to_csv(t.id)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="inbox_{t.id}.csv"'},
    )


@app.post("/api/sessions/{sid}/summary_audio")
def summary_audio(sid: str) -> dict:
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


@app.get("/widget")
def widget_page() -> FileResponse:
    return FileResponse(WEB / "widget.html")


@app.get("/embed.js")
def embed_script() -> FileResponse:
    return FileResponse(WEB / "embed.js", media_type="application/javascript")


@app.get("/demo/company.html")
def demo_company_page() -> FileResponse:
    return FileResponse(WEB / "demo" / "company.html")


@app.get("/inbox")
def inbox_page() -> FileResponse:
    return FileResponse(WEB / "inbox.html")


@app.get("/eval")
def eval_page() -> FileResponse:
    return FileResponse(WEB / "eval.html")


@app.get("/limits")
def limits_page() -> FileResponse:
    return FileResponse(WEB / "limits.html")


app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
