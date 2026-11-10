# -*- coding: utf-8 -*-
"""Offline tests for the configurable Gnani adapter helpers (skipped silently if httpx is missing)."""
import os


def _mod():
    try:
        from app.providers import gnani
        return gnani
    except ImportError:
        return None


def test_dig_and_subst():
    g = _mod()
    if g is None:
        return
    assert g._dig({"data": {"text": "హాయ్"}}, "data.text") == "హాయ్"
    assert g._dig({"r": [{"t": "x"}]}, "r.0.t") == "x"
    assert g._subst({"a": "{text}", "b": ["{lang}", 1]}, {"text": "hi", "lang": "te"}) == {"a": "hi", "b": ["te", 1]}


def test_unconfigured_provider_raises_clear_error():
    g = _mod()
    if g is None:
        return
    from app.providers.base import NotConfiguredError
    for k in ("GNANI_STT_URL", "GNANI_STT_TEXT_PATH", "GNANI_TTS_URL"):
        os.environ.pop(k, None)
    p = g.GnaniProvider()
    for call in (lambda: p.transcribe(b"x"), lambda: p.synthesize("x")):
        try:
            call()
        except NotConfiguredError:
            continue
        raise AssertionError("expected NotConfiguredError")


def test_bad_auth_template_is_rejected():
    g = _mod()
    if g is None:
        return
    from app.providers.base import NotConfiguredError
    os.environ["GNANI_API_KEY"] = "k"
    os.environ["GNANI_STT_AUTH"] = "no-colon-here"
    try:
        g.GnaniProvider()._headers("GNANI_STT_AUTH")
    except NotConfiguredError:
        return
    finally:
        os.environ.pop("GNANI_STT_AUTH", None); os.environ.pop("GNANI_API_KEY", None)
    raise AssertionError("expected NotConfiguredError")
