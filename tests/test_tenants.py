# -*- coding: utf-8 -*-
from pathlib import Path
import pytest
from app.core.tenants import load_tenant, load_tenants, TenantDef

TENANTS_DIR = Path(__file__).resolve().parent.parent / "tenants"


def test_load_demo_company():
    t_map = load_tenants(TENANTS_DIR)
    assert "demo_company" in t_map
    t = t_map["demo_company"]
    assert t.id == "demo_company"
    assert t.public_key == "pk_demo_change_me"
    assert t.company_language == "en"
    assert "farmer_scheme" in t.forms


def test_tenant_origin_matching():
    t = TenantDef(
        id="test",
        name="Test",
        company_language="en",
        public_key="pk_test",
        allowed_origins=["http://localhost:8000", "https://*.onrender.com"],
    )
    assert t.is_origin_allowed("http://localhost:8000")
    assert t.is_origin_allowed("https://my-app.onrender.com")
    assert not t.is_origin_allowed("https://malicious.com")
    assert t.is_origin_allowed("null")


def test_tenant_admin_token_fallback():
    t = TenantDef(
        id="test",
        name="Test",
        company_language="en",
        public_key="pk_123",
        admin_token_env="NONEXISTENT_ENV_VAR",
    )
    assert t.get_admin_token() == "demo_token_pk_123"
