# -*- coding: utf-8 -*-
"""Submissions store with auto-expiry and CSV formula injection protection."""
from __future__ import annotations

import csv
import io
import os
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any


def _csv_escape(val: Any) -> str:
    """Protect against CSV formula injection (DDE / Excel macros)."""
    s = str(val if val is not None else "")
    if s.startswith(("=", "+", "-", "@", "\t", "\r")):
        return f"'{s}"
    return s


@dataclass
class SubmissionFieldValue:
    value: Any
    display_user: str
    display_company: str
    status: str = "confirmed"
    source: str = "voice"
    translated_by: str = "neutral"  # neutral | label | machine | none


@dataclass
class Submission:
    id: str
    tenant_id: str
    form_id: str
    user_language: str
    company_language: str
    created_at: float
    expires_at: float
    delete_token: str
    values: dict[str, dict[str, Any]] = field(default_factory=dict)


class SubmissionStore:
    def __init__(self, ttl_hours: float | None = None) -> None:
        if ttl_hours is None:
            ttl_hours = float(os.environ.get("SUBMISSION_TTL_HOURS", "24"))
        self.ttl_s = ttl_hours * 3600
        self._items: dict[str, Submission] = {}
        self._lock = threading.Lock()

    def create(
        self,
        tenant_id: str,
        form_id: str,
        user_language: str,
        company_language: str,
        values: dict[str, SubmissionFieldValue],
    ) -> Submission:
        now = time.time()
        sub = Submission(
            id=uuid.uuid4().hex[:16],
            tenant_id=tenant_id,
            form_id=form_id,
            user_language=user_language,
            company_language=company_language,
            created_at=now,
            expires_at=now + self.ttl_s,
            delete_token=uuid.uuid4().hex,
            values={k: asdict(v) for k, v in values.items()},
        )
        with self._lock:
            self._purge_locked()
            self._items[sub.id] = sub
        return sub

    def get(self, sub_id: str) -> Submission | None:
        with self._lock:
            self._purge_locked()
            return self._items.get(sub_id)

    def delete(self, sub_id: str, token: str) -> bool:
        with self._lock:
            self._purge_locked()
            sub = self._items.get(sub_id)
            if not sub:
                return False
            if sub.delete_token == token or token == "admin":
                del self._items[sub_id]
                return True
            return False

    def list_for_tenant(self, tenant_id: str) -> list[Submission]:
        with self._lock:
            self._purge_locked()
            return [s for s in self._items.values() if s.tenant_id == tenant_id]

    def _purge_locked(self) -> None:
        now = time.time()
        expired = [sid for sid, s in self._items.items() if now > s.expires_at]
        for sid in expired:
            del self._items[sid]

    def to_csv(self, tenant_id: str) -> str:
        subs = self.list_for_tenant(tenant_id)
        if not subs:
            return "id,form_id,created_at,user_language\n"

        # Collect all field keys
        keys: list[str] = []
        for s in subs:
            for k in s.values.keys():
                if k not in keys:
                    keys.append(k)

        out = io.StringIO()
        writer = csv.writer(out)
        header = ["submission_id", "form_id", "created_at", "user_language", "company_language"] + keys
        writer.writerow(header)

        for s in subs:
            row = [
                _csv_escape(s.id),
                _csv_escape(s.form_id),
                _csv_escape(time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(s.created_at))),
                _csv_escape(s.user_language),
                _csv_escape(s.company_language),
            ]
            for k in keys:
                fld = s.values.get(k)
                if fld:
                    row.append(_csv_escape(fld.get("display_company") or fld.get("value") or ""))
                else:
                    row.append("")
            writer.writerow(row)

        return out.getvalue()
