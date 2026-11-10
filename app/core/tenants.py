# -*- coding: utf-8 -*-
"""Tenant configurations for Bolo Form embed & inbox."""
from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import yaml


@dataclass
class TenantDef:
    id: str
    name: str
    company_language: str
    public_key: str
    allowed_origins: list[str] = field(default_factory=list)
    admin_token_env: str = ""
    forms: list[str] = field(default_factory=list)

    def is_origin_allowed(self, origin: str) -> bool:
        if not origin:
            return False
        # Normalize
        origin = origin.strip().lower()
        if origin in ("null", "file://"):
            return True
        for pattern in self.allowed_origins:
            pat = pattern.strip().lower()
            if pat == "*" or pat == origin:
                return True
            if fnmatch.fnmatch(origin, pat):
                return True
        return False

    def get_admin_token(self) -> str:
        if self.admin_token_env:
            token = os.environ.get(self.admin_token_env, "").strip()
            if token:
                return token
        return "demo_token_" + self.public_key


def load_tenant(path: Path) -> TenantDef:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid tenant YAML in {path.name}")
    for req in ("id", "name", "public_key"):
        if not raw.get(req):
            raise ValueError(f"Tenant {path.name} missing required field {req!r}")
    return TenantDef(
        id=raw["id"],
        name=raw["name"],
        company_language=raw.get("company_language", "en"),
        public_key=raw["public_key"],
        allowed_origins=list(raw.get("allowed_origins", [])),
        admin_token_env=raw.get("admin_token_env", ""),
        forms=list(raw.get("forms", [])),
    )


def load_tenants(directory: Path) -> dict[str, TenantDef]:
    tenants: dict[str, TenantDef] = {}
    if not directory.exists():
        return tenants
    for p in sorted(directory.glob("*.yaml")):
        t = load_tenant(p)
        tenants[t.id] = t
    return tenants
