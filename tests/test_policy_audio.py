# -*- coding: utf-8 -*-
import numpy as np
from pathlib import Path
from app.audio.degrade import add_noise, telephony, apply_condition, CONDITIONS
from app.audio.wav import read_wav, write_wav
from app.core.confirm_policy import decide_confirm_mode, risk_score
from app.core.forms import load_forms
from app.core.noise_estimate import estimate_snr_db
from app.core.parsers import ParseResult

FORMS = load_forms(Path(__file__).resolve().parent.parent / "app" / "forms")
F = {f.key: f for f in FORMS["farmer_scheme"].fields}
OK = ParseResult(True, "x", "x", "x", "x")
AMBIG = ParseResult(True, "x", "x", "x", "x", ambiguous=True)


def speechlike(sr=16000, seconds=2.0):
    t = np.arange(int(sr * seconds)) / sr
    env = (np.sin(2 * np.pi * 2 * t) > 0).astype(np.float32)       # bursts with gaps
    return (0.4 * env * np.sin(2 * np.pi * 220 * t)).astype(np.float32)


def test_critical_fields_always_confirmed():
    for policy in ("adaptive", "always"):
        assert decide_confirm_mode(F["phone"], OK, 0.99, 40, 0, policy) == "digits"
        assert decide_confirm_mode(F["land_acres"], OK, 0.99, 40, 0, policy) == "explicit"


def test_policy_baselines():
    assert decide_confirm_mode(F["crop"], OK, None, None, 0, "never") == "implicit"
    assert decide_confirm_mode(F["crop"], OK, None, None, 0, "always") == "explicit"


def test_policy_monotonic_with_noise_confidence_ambiguity_attempts():
    base = risk_score(F["crop"], OK, 0.9, 30, 0)
    assert risk_score(F["crop"], OK, 0.5, 30, 0) > base
    assert risk_score(F["crop"], OK, 0.9, 5, 0) > base
    assert risk_score(F["crop"], AMBIG, 0.9, 30, 0) > base
    assert risk_score(F["crop"], OK, 0.9, 30, 2) > base
    assert risk_score(F["name"], OK, 0.9, 30, 0) > base            # medium > low


def test_low_risk_clean_audio_is_implicit_and_noisy_is_not():
    assert decide_confirm_mode(F["crop"], OK, 0.95, 30, 0) == "implicit"
    assert decide_confirm_mode(F["crop"], OK, 0.95, 8, 1) != "implicit"
    assert decide_confirm_mode(F["crop"], AMBIG, 0.5, 8, 1) in ("simple", "explicit")


def test_wav_roundtrip():
    x = speechlike()
    y, sr = read_wav(write_wav(x, 16000))
    assert sr == 16000 and len(y) == len(x) and np.max(np.abs(x - y)) < 1e-3


def test_read_wav_rejects_garbage():
    try:
        read_wav(b"not a wav")
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_add_noise_hits_target_snr():
    x = speechlike()
    wav = write_wav(x, 16000)
    rng = np.random.default_rng(0)
    for snr in (20, 10, 5):
        y, _ = read_wav(add_noise(wav, snr, rng))
        noise = y - x
        got = 10 * np.log10(np.mean(x ** 2) / np.mean(noise ** 2))
        assert abs(got - snr) < 1.0, (snr, got)


def test_telephony_removes_high_frequencies():
    sr = 16000
    t = np.arange(sr) / sr
    x = (0.3 * np.sin(2 * np.pi * 1000 * t) + 0.3 * np.sin(2 * np.pi * 6000 * t)).astype(np.float32)
    y, _ = read_wav(telephony(write_wav(x, sr)))
    spec = np.abs(np.fft.rfft(y))
    f = np.fft.rfftfreq(len(y), 1 / sr)
    low, high = spec[(f > 900) & (f < 1100)].max(), spec[(f > 5900) & (f < 6100)].max()
    assert high < low * 0.1


def test_all_conditions_return_valid_wav():
    wav = write_wav(speechlike(), 16000)
    rng = np.random.default_rng(1)
    for c in CONDITIONS:
        y, sr = read_wav(apply_condition(wav, c, rng))
        assert sr == 16000 and len(y) > 0


def test_snr_estimate_orders_clean_above_noisy_and_handles_short():
    x = speechlike()
    rng = np.random.default_rng(2)
    clean = estimate_snr_db(write_wav(x + 0.002 * rng.standard_normal(len(x)).astype(np.float32), 16000))
    noisy = estimate_snr_db(add_noise(write_wav(x, 16000), 5, rng))
    assert clean is not None and noisy is not None and clean > noisy
    assert estimate_snr_db(write_wav(x[:100], 16000)) is None
    assert estimate_snr_db(b"garbage") is None
