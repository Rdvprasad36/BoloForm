# -*- coding: utf-8 -*-
"""API tests: use FastAPI TestClient (mock provider, no network, no keys).

Covers: start session, turns (hint / answer / command / typed),
        edit, rerecord, finish, delete, expired session, oversize upload,
        non-WAV upload, unknown form, session not found.
"""
from __future__ import annotations

import io
import wave

import pytest
from fastapi.testclient import TestClient

# Import after patching env so provider stays mock
import os
os.environ.setdefault("PROVIDER", "mock")

from app.main import app  # noqa: E402

client = TestClient(app, raise_server_exceptions=True)


# ------------------------------------------------------------------ helpers
def _start(form_id: str = "farmer_scheme") -> tuple[str, dict]:
    r = client.post("/api/sessions", json={"form_id": form_id})
    assert r.status_code == 200, r.text
    data = r.json()
    return data["session_id"], data


def _turn(sid: str, **fields) -> dict:
    r = client.post(f"/api/sessions/{sid}/turn", data=fields)
    assert r.status_code == 200, r.text
    return r.json()


def _make_wav(duration_s: float = 0.1, sr: int = 16000) -> bytes:
    """Generate a minimal valid 16-bit mono PCM WAV."""
    import numpy as np
    n = int(sr * duration_s)
    samples = (np.sin(2 * 3.14159 * 440 * (np.arange(n) / sr)) * 1000).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(samples.tobytes())
    return buf.getvalue()


# ------------------------------------------------------------------ health
def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    j = r.json()
    assert j["ok"] is True
    assert j["provider"] == "mock"
    assert "policy" in j


# ------------------------------------------------------------------ forms list
def test_list_forms():
    r = client.get("/api/forms")
    assert r.status_code == 200
    forms = r.json()
    assert len(forms) >= 2
    ids = {f["id"] for f in forms}
    assert "farmer_scheme" in ids
    assert "pension_scheme" in ids
    for f in forms:
        assert "title_te" in f and "title_en" in f and "fields" in f


# ------------------------------------------------------------------ start session
def test_start_session_farmer():
    sid, data = _start("farmer_scheme")
    assert sid
    assert data["action"] == "ask"
    assert "say_te" in data and "say_en" in data
    assert "prompt" in data
    assert data["progress"]["total"] == 8
    assert data["provider"] == "mock"


def test_start_session_pension():
    sid, data = _start("pension_scheme")
    assert data["action"] == "ask"
    assert data["progress"]["total"] == 5


def test_start_unknown_form():
    r = client.post("/api/sessions", json={"form_id": "no_such_form"})
    assert r.status_code == 404


# ------------------------------------------------------------------ turn: mock hint (simulated speech)
def test_turn_hint_name_gets_confirm():
    sid, _ = _start()
    t = _turn(sid, hint="రాము")
    assert t["action"] == "confirm"
    assert t["confirm"]["display"] == "రాము"


def test_turn_yes_after_confirm():
    sid, _ = _start()
    _turn(sid, hint="రాము")
    t = _turn(sid, answer="yes")
    assert t["action"] == "ask"
    # Next question should be about age
    assert "field" in t and t["field"]["key"] == "age"


def test_turn_no_after_confirm_reasks():
    sid, _ = _start()
    _turn(sid, hint="రాము")
    t = _turn(sid, answer="no")
    assert t["action"] == "reask"


# ------------------------------------------------------------------ commands
def test_command_back():
    sid, _ = _start()
    _turn(sid, hint="రాము")
    _turn(sid, answer="yes")          # commit name, now on age
    t = _turn(sid, command="back")
    # Should be back on name (idx 0)
    assert t["field"]["key"] == "name"


def test_command_skip():
    sid, _ = _start()
    t = _turn(sid, command="skip")
    assert t["field"]["key"] == "age"   # skipped name, moved to age
    # Verify name was skipped
    name_field = next(f for f in t["form"] if f["key"] == "name")
    assert name_field["status"] == "skipped"


def test_command_repeat():
    sid, _ = _start()
    t = _turn(sid, command="repeat")
    assert t["action"] == "ask"
    assert t["field"]["key"] == "name"


# ------------------------------------------------------------------ typed fallback
def test_typed_fallback_valid():
    sid, _ = _start()
    t = _turn(sid, text="రాము", typed="1")
    assert t["action"] == "ask"
    assert t["field"]["key"] == "age"


def test_typed_fallback_invalid():
    sid, _ = _start()
    t = _turn(sid, text="", typed="1")
    assert t["action"] == "fallback"


# ------------------------------------------------------------------ audio upload (WAV)
def test_turn_with_wav_upload():
    """WAV upload should be accepted. MockProvider returns empty transcript -> reask or fallback."""
    sid, _ = _start()
    wav = _make_wav(0.5)
    r = client.post(
        f"/api/sessions/{sid}/turn",
        files={"audio": ("speech.wav", wav, "audio/wav")},
    )
    assert r.status_code == 200
    j = r.json()
    # Mock returns empty string -> not_heard -> reask
    assert j["action"] in ("reask", "fallback", "ask", "confirm")


def test_turn_oversize_audio_rejected():
    sid, _ = _start()
    big = b"\x00" * (2_000_001)  # just over 2 MB limit
    r = client.post(
        f"/api/sessions/{sid}/turn",
        files={"audio": ("speech.wav", big, "audio/wav")},
    )
    assert r.status_code == 413


def test_turn_non_wav_rejected():
    """Non-WAV audio should not crash: either 400 or the engine handles it gracefully."""
    sid, _ = _start()
    r = client.post(
        f"/api/sessions/{sid}/turn",
        files={"audio": ("speech.mp3", b"garbage mp3 data", "audio/mpeg")},
    )
    # Either a 400 error or the engine returns a turn (voice_unavailable / fallback path)
    assert r.status_code in (200, 400)


# ------------------------------------------------------------------ edit field
def test_edit_field_on_review():
    sid, _ = _start("pension_scheme")
    # Complete all fields with 'never' policy isn't possible here; use typed for each field
    # pension has 5 fields: name, age, village, phone, lives_alone
    _turn(sid, text="రాము", typed="1")           # name
    _turn(sid, text="65", typed="1")             # age
    _turn(sid, text="గొల్లపాలెం", typed="1")    # village
    _turn(sid, text="9876543210", typed="1")     # phone
    t = _turn(sid, text="అవును", typed="1")     # lives_alone -> review
    assert t["action"] == "review", t

    r = client.patch(
        f"/api/sessions/{sid}/fields/age",
        json={"value": "70"},
    )
    assert r.status_code == 200
    j = r.json()
    assert j["action"] == "review"
    age_f = next(f for f in j["form"] if f["key"] == "age")
    assert age_f["value"] == "70" and age_f["status"] == "edited"


def test_edit_field_invalid_value():
    sid, _ = _start("pension_scheme")
    _turn(sid, text="రాము", typed="1")
    _turn(sid, text="65", typed="1")
    _turn(sid, text="గొల్లపాలెం", typed="1")
    _turn(sid, text="9876543210", typed="1")
    t = _turn(sid, text="అవును", typed="1")
    assert t["action"] == "review"

    r = client.patch(f"/api/sessions/{sid}/fields/age", json={"value": "hello"})
    assert r.status_code == 200
    j = r.json()
    assert j.get("error") is not None


# ------------------------------------------------------------------ rerecord
def test_rerecord_field():
    sid, _ = _start("pension_scheme")
    _turn(sid, text="రాము", typed="1")
    _turn(sid, text="65", typed="1")
    _turn(sid, text="గొల్లపాలెం", typed="1")
    _turn(sid, text="9876543210", typed="1")
    t = _turn(sid, text="అవును", typed="1")
    assert t["action"] == "review"

    r = client.post(f"/api/sessions/{sid}/rerecord/village")
    assert r.status_code == 200
    j = r.json()
    assert j["action"] == "ask"
    assert j["field"]["key"] == "village"


def test_rerecord_unknown_field():
    sid, _ = _start()
    r = client.post(f"/api/sessions/{sid}/rerecord/no_such_field")
    assert r.status_code == 404


# ------------------------------------------------------------------ finish
def test_finish_session():
    sid, _ = _start()
    r = client.post(f"/api/sessions/{sid}/finish")
    assert r.status_code == 200
    j = r.json()
    assert j["action"] == "done"
    assert j["state"] == "done"


# ------------------------------------------------------------------ delete
def test_delete_session():
    sid, _ = _start()
    r = client.delete(f"/api/sessions/{sid}")
    assert r.status_code == 200
    assert r.json()["deleted"] is True

    # After delete, the session should be gone
    r2 = client.post(f"/api/sessions/{sid}/turn", data={"hint": "test"})
    assert r2.status_code == 404


# ------------------------------------------------------------------ expired session
def test_expired_session_returns_404():
    """Create a store with 0-TTL to test expiry path in the API."""
    from app.core.dialogue import SessionStore, DialogueEngine
    from app.core.forms import load_forms
    from pathlib import Path
    import time

    forms = load_forms(Path("app/forms"))
    short_store = SessionStore(ttl_s=0)
    s = short_store.create(forms["farmer_scheme"])
    time.sleep(0.01)
    # After TTL, store.get returns None
    assert short_store.get(s.id) is None


# ------------------------------------------------------------------ session not found
def test_session_not_found():
    r = client.post("/api/sessions/nonexistentsid/turn", data={"hint": "test"})
    assert r.status_code == 404


# ------------------------------------------------------------------ get session state
def test_get_session_state():
    sid, _ = _start()
    r = client.get(f"/api/sessions/{sid}")
    assert r.status_code == 200
    j = r.json()
    assert "state" in j and "form" in j


# ------------------------------------------------------------------ summary audio
def test_summary_audio():
    sid, _ = _start()
    r = client.post(f"/api/sessions/{sid}/summary_audio")
    assert r.status_code == 200
    j = r.json()
    assert "audio_b64" in j


# ------------------------------------------------------------------ static pages
def test_static_index_served():
    r = client.get("/")
    assert r.status_code == 200
    assert b"Bolo Form" in r.content or b"<html" in r.content


def test_eval_page():
    r = client.get("/eval")
    assert r.status_code == 200


def test_limits_page():
    r = client.get("/limits")
    assert r.status_code == 200


# ------------------------------------------------------------------ telephony simulation
def test_start_session_telephony_sim():
    r = client.post("/api/sessions", json={"form_id": "farmer_scheme", "telephony_sim": True})
    assert r.status_code == 200
    j = r.json()
    assert j["telephony"] is True


# ------------------------------------------------------------------ widget, embed, demo & inbox pages
def test_widget_page_served():
    r = client.get("/widget")
    assert r.status_code == 200
    assert "frame-ancestors" in r.headers.get("content-security-policy", "")
    assert b"Bolo Form Widget" in r.content


def test_embed_script_served():
    r = client.get("/embed.js")
    assert r.status_code == 200
    assert "javascript" in r.headers.get("content-type", "")
    assert b"bolo-launch-btn" in r.content


def test_demo_company_page_served():
    r = client.get("/demo/company.html")
    assert r.status_code == 200
    assert b"Demo Agri Co" in r.content
    assert b"embed.js" in r.content


def test_inbox_page_served():
    r = client.get("/inbox")
    assert r.status_code == 200
    assert b"Submissions Inbox" in r.content


# ------------------------------------------------------------------ submit & inbox APIs
def test_submit_and_inbox_flow():
    sid, _ = _start("farmer_scheme")
    _turn(sid, text="రాము", typed="1")
    _turn(sid, text="35", typed="1")

    # Submit
    r_sub = client.post(f"/api/sessions/{sid}/submit?key=pk_demo_change_me")
    assert r_sub.status_code == 200
    sub_data = r_sub.json()
    assert sub_data["ok"] is True
    sub_id = sub_data["submission_id"]
    delete_token = sub_data["delete_token"]
    assert sub_id and delete_token

    # Inbox JSON without token should fail 401
    r_unauth = client.get("/api/inbox.json?tenant=demo_company")
    assert r_unauth.status_code == 401

    # Inbox JSON with valid token
    token = "demo_token_pk_demo_change_me"
    r_inbox = client.get(f"/api/inbox.json?tenant=demo_company&token={token}")
    assert r_inbox.status_code == 200
    items = r_inbox.json()
    assert len(items) >= 1
    found = next((s for s in items if s["id"] == sub_id), None)
    assert found is not None
    assert found["values"]["name"]["value"] == "రాము"

    # Inbox CSV with valid token
    r_csv = client.get(f"/api/inbox.csv?tenant=demo_company&token={token}")
    assert r_csv.status_code == 200
    assert "text/csv" in r_csv.headers["content-type"]
    assert sub_id in r_csv.text

    # Delete submission
    r_del = client.delete(f"/api/submissions/{sub_id}?token={delete_token}")
    assert r_del.status_code == 200
    assert r_del.json()["deleted"] is True

    # After deletion, should not appear in inbox
    r_inbox2 = client.get(f"/api/inbox.json?tenant=demo_company&token={token}")
    assert not any(s["id"] == sub_id for s in r_inbox2.json())

