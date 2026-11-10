# -*- coding: utf-8 -*-
"""Dialogue engine: pure Python, no audio, no network. Fully testable.

States: ask -> (confirm) -> ask ... -> review -> done
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from . import lexicon_te as L
from .confirm_policy import decide_confirm_mode
from .forms import FieldDef, FormDef
from .parsers import ParseResult, detect_command, parse_field, parse_yes_no_raw

MAX_RETRIES = 2            # failed hearings/rejections before the typed fallback is offered
SESSION_TTL_S = 600        # 10 minutes idle -> purged
LOW_CONFIDENCE = 0.6


@dataclass
class FieldState:
    value: Any = None
    display: str = ""
    display_en: str = ""
    status: str = "empty"      # empty|confirmed|implicit|typed|edited|skipped|needs_check
    source: str = ""           # voice|typed


@dataclass
class Pending:
    field_key: str
    parsed: ParseResult
    mode: str
    confidence: float | None = None


@dataclass
class Session:
    id: str
    form: FormDef
    telephony: bool = False
    tenant_id: str | None = None
    demo_code_ok: bool = False
    idx: int = 0
    fields: dict[str, FieldState] = field(default_factory=dict)
    state: str = "ask"
    retries: int = 0
    pending: Pending | None = None
    return_to_review: bool = False
    turns: int = 0
    last_seen: float = field(default_factory=time.time)
    last_snr: float | None = None

    @property
    def field_def(self) -> FieldDef:
        return self.form.fields[self.idx]


class SessionStore:
    """In-memory sessions with idle expiry. No audio or transcripts are kept."""

    def __init__(self, ttl_s: int = SESSION_TTL_S):
        self._items: dict[str, Session] = {}
        self._lock = threading.Lock()
        self.ttl_s = ttl_s

    def create(self, form: FormDef, telephony: bool = False,
               tenant_id: str | None = None, demo_code_ok: bool = False) -> Session:
        s = Session(id=uuid.uuid4().hex, form=form, telephony=telephony,
                    tenant_id=tenant_id, demo_code_ok=demo_code_ok,
                    fields={f.key: FieldState() for f in form.fields})
        with self._lock:
            self._purge_locked()
            self._items[s.id] = s
        return s

    def get(self, sid: str) -> Session | None:
        with self._lock:
            self._purge_locked()
            s = self._items.get(sid)
            if s:
                s.last_seen = time.time()
            return s

    def delete(self, sid: str) -> bool:
        with self._lock:
            return self._items.pop(sid, None) is not None

    def _purge_locked(self) -> None:
        now = time.time()
        for sid in [k for k, v in self._items.items() if now - v.last_seen > self.ttl_s]:
            del self._items[sid]


class DialogueEngine:
    def __init__(self, policy: str = "adaptive"):
        self.policy = policy

    # ------------------------------------------------------------ turn builders
    def _form_view(self, s: Session) -> list[dict]:
        out = []
        for f in s.form.fields:
            st = s.fields[f.key]
            out.append({"key": f.key, "label_te": f.label_te, "label_en": f.label_en,
                        "value": st.display, "value_en": st.display_en or st.display,
                        "status": st.status})
        return out

    def _turn(self, s: Session, action: str, say_te: str, say_en: str, **extra) -> dict:
        s.turns += 1
        fld = s.field_def if s.idx < len(s.form.fields) else None
        turn = {
            "action": action,
            "state": s.state,
            "say_te": say_te,
            "say_en": say_en,
            "progress": {"index": min(s.idx, len(s.form.fields)), "total": len(s.form.fields)},
            "field": ({"key": fld.key, "type": fld.type, "label_te": fld.label_te,
                       "label_en": fld.label_en, "prompt_te": fld.prompt_te,
                       "prompt_en": fld.prompt_en} if fld and s.state in ("ask", "confirm") else None),
            "form": self._form_view(s),
            "confirm": None,
        }
        if s.pending and s.state == "confirm":
            p = s.pending
            turn["confirm"] = {"mode": p.mode, "display": p.parsed.display,
                               "display_en": p.parsed.display_en}
        turn.update(extra)
        return turn

    def _question(self, s: Session, action: str = "ask", prefix: tuple[str, str] | None = None) -> dict:
        f = s.field_def
        te, en = f.prompt_te, f.prompt_en
        if prefix:
            te, en = f"{prefix[0]} {te}", f"{prefix[1]} {en}"
        return self._turn(s, action, te, en)

    def _msg(self, key: str) -> tuple[str, str]:
        return L.MSG[key]

    # ------------------------------------------------------------ public API
    def start(self, s: Session) -> dict:
        s.state, s.idx = "ask", 0
        g_te, g_en = self._msg("greeting")
        return self._question(s, "ask", prefix=(g_te, g_en))

    def handle_utterance(self, s: Session, text: str, confidence: float | None = None,
                         snr_db: float | None = None) -> dict:
        """Process a transcript (from voice). Never raises on bad user input."""
        s.last_snr = snr_db
        if s.state == "done":
            return self._turn(s, "done", *self._msg("done"))
        if s.state == "review":
            return self._turn(s, "review", *self._msg("review"), message_key="use_edit")
        if not (text or "").strip():
            return self._not_heard(s, "empty")
        if s.state == "confirm":
            return self._on_confirm(s, text)
        return self._on_ask(s, text, confidence, snr_db)

    def handle_typed(self, s: Session, text: str) -> dict:
        """Typed fallback: parsed and validated like voice, committed without read-back."""
        if s.state in ("review", "done"):
            return self._turn(s, s.state, *self._msg(s.state if s.state == "done" else "review"))
        s.pending, s.state = None, "ask"
        r = parse_field(s.field_def, text)
        if not r.ok:
            te, en = self._msg(r.error if r.error in L.MSG else "no_match")
            return self._turn(s, "fallback", te, en, error=r.error)
        self._commit(s, r, status="needs_check", source="typed")
        return self._advance(s)

    def edit_field(self, s: Session, key: str, text: str) -> dict:
        """Manual edit from the review screen."""
        try:
            idx = s.form.field_index(key)
        except KeyError:
            return self._turn(s, "review", *self._msg("review"), error="unknown_field")
        r = parse_field(s.form.fields[idx], text)
        if not r.ok:
            te, en = self._msg(r.error if r.error in L.MSG else "no_match")
            return self._turn(s, "review", te, en, error=r.error)
        st = s.fields[key]
        st.value, st.display, st.display_en = r.value, r.display, r.display_en
        st.status, st.source = "edited", "typed"
        return self._turn(s, "review", *self._msg("review"))

    def rerecord(self, s: Session, key: str) -> dict:
        """Review screen: re-ask one field by voice, then return to review."""
        s.idx = s.form.field_index(key)
        s.state, s.pending, s.retries, s.return_to_review = "ask", None, 0, True
        return self._question(s, "ask")

    def voice_unavailable(self, s: Session) -> dict:
        """The speech service failed: offer the typed fallback instead of getting stuck."""
        s.pending = None if s.state == "confirm" else s.pending
        if s.state == "confirm":
            s.state = "ask"
        return self._turn(s, "fallback", *self._msg("fallback"), error="voice_unavailable")

    def finish(self, s: Session) -> dict:
        s.state = "done"
        return self._turn(s, "done", *self._msg("done"))

    # ------------------------------------------------------------ internals
    def _not_heard(self, s: Session, key: str) -> dict:
        s.retries += 1
        if s.retries >= MAX_RETRIES:
            return self._turn(s, "fallback", *self._msg("fallback"), error=key)
        return self._turn(s, "reask", *self._msg(key if key in L.MSG else "no_match"), error=key)

    def _on_ask(self, s: Session, text: str, confidence: float | None, snr_db: float | None) -> dict:
        cmd = detect_command(text)
        if cmd == "repeat":
            return self._question(s, "ask")
        if cmd == "back":
            if s.idx > 0 and not s.return_to_review:
                s.idx -= 1
                s.fields[s.field_def.key] = FieldState()
                s.retries = 0
            return self._question(s, "ask")
        if cmd == "skip":
            s.fields[s.field_def.key] = FieldState(status="skipped")
            te, en = self._msg("skipped")
            nxt = self._advance(s)
            nxt["say_te"], nxt["say_en"] = f"{te} {nxt['say_te']}", f"{en} {nxt['say_en']}"
            return nxt

        r = parse_field(s.field_def, text)
        if not r.ok:
            return self._not_heard(s, r.error if r.error in L.MSG else "no_match")

        mode = decide_confirm_mode(s.field_def, r, confidence, snr_db, s.retries, self.policy)
        if mode == "implicit":
            status = "needs_check" if (confidence is not None and confidence < LOW_CONFIDENCE) else "implicit"
            self._commit(s, r, status=status, source="voice")
            return self._advance(s)

        s.pending = Pending(s.field_def.key, r, mode, confidence)
        s.state = "confirm"
        return self._readback(s)

    def _readback(self, s: Session) -> dict:
        p = s.pending
        assert p is not None
        q_te, q_en = self._msg("confirm_q")
        return self._turn(s, "confirm", f"{p.parsed.spoken_te}. {q_te}",
                          f"{p.parsed.display_en}. {q_en}")

    def _on_confirm(self, s: Session, text: str) -> dict:
        cmd = detect_command(text)
        if cmd == "repeat":
            return self._readback(s)
        if cmd == "back":
            s.pending, s.state = None, "ask"
            return self._question(s, "ask")
        ans = parse_yes_no_raw(text)
        if ans is None:
            return self._turn(s, "confirm", *self._msg("yes_no_unclear"),
                              confirm=self._turn_confirm(s))
        p = s.pending
        assert p is not None
        if ans:
            self._commit(s, p.parsed, status="confirmed", source="voice")
            return self._advance(s)
        # rejected: discard, make the next attempt stricter, maybe offer typing
        s.pending, s.state = None, "ask"
        s.retries += 1
        if s.retries >= MAX_RETRIES:
            return self._turn(s, "fallback", *self._msg("fallback"), error="rejected")
        return self._question(s, "reask", prefix=self._msg("after_no"))

    def _turn_confirm(self, s: Session) -> dict | None:
        p = s.pending
        return {"mode": p.mode, "display": p.parsed.display, "display_en": p.parsed.display_en} if p else None

    def _commit(self, s: Session, r: ParseResult, status: str, source: str) -> None:
        st = s.fields[s.field_def.key]
        st.value, st.display, st.display_en = r.value, r.display, r.display_en
        st.status, st.source = status, source

    def _advance(self, s: Session) -> dict:
        s.retries, s.pending = 0, None
        if s.return_to_review:
            s.return_to_review, s.state = False, "review"
            s.idx = len(s.form.fields)
            return self._turn(s, "review", *self._msg("review"))
        s.idx += 1
        if s.idx >= len(s.form.fields):
            s.state = "review"
            return self._turn(s, "review", *self._msg("review"))
        s.state = "ask"
        return self._question(s, "ask")
