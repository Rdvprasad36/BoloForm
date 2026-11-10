# -*- coding: utf-8 -*-
import time
import pytest
from app.core.submissions import SubmissionStore, SubmissionFieldValue, _csv_escape


def test_csv_formula_injection_escaping():
    assert _csv_escape("normal") == "normal"
    assert _csv_escape("=CMD|' /C calc'!A0") == "'=CMD|' /C calc'!A0"
    assert _csv_escape("+123") == "'+123"
    assert _csv_escape("-456") == "'-456"
    assert _csv_escape("@SUM(A1:A10)") == "'@SUM(A1:A10)"


def test_submission_lifecycle():
    store = SubmissionStore(ttl_hours=1.0)
    sub = store.create(
        tenant_id="demo_company",
        form_id="farmer_scheme",
        user_language="te",
        company_language="en",
        values={
            "name": SubmissionFieldValue("Ramu", "రాము", "Ramu", "confirmed", "voice"),
            "age": SubmissionFieldValue(35, "35", "35", "confirmed", "voice"),
        },
    )
    assert sub.id
    assert sub.delete_token

    # Fetch
    fetched = store.get(sub.id)
    assert fetched is not None
    assert fetched.values["name"]["value"] == "Ramu"

    # List
    lst = store.list_for_tenant("demo_company")
    assert len(lst) == 1
    assert lst[0].id == sub.id

    # CSV output
    csv_text = store.to_csv("demo_company")
    assert "submission_id" in csv_text
    assert "Ramu" in csv_text

    # Delete with wrong token fails
    assert not store.delete(sub.id, "wrong_token")
    assert store.get(sub.id) is not None

    # Delete with correct token succeeds
    assert store.delete(sub.id, sub.delete_token)
    assert store.get(sub.id) is None


def test_submission_expiry():
    store = SubmissionStore(ttl_hours=0.0) # immediate expiry
    sub = store.create("t1", "f1", "te", "en", {})
    time.sleep(0.01)
    assert store.get(sub.id) is None
