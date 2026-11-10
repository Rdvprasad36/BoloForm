# -*- coding: utf-8 -*-
from pathlib import Path
from app.core.dialogue import DialogueEngine, SessionStore
from app.core.forms import load_forms

FORMS = load_forms(Path(__file__).resolve().parent.parent / "app" / "forms")


def new(policy="adaptive", form="farmer_scheme"):
    eng = DialogueEngine(policy)
    s = SessionStore().create(FORMS[form])
    return eng, s, eng.start(s)


def say(eng, s, text, conf=None, snr=25.0):
    return eng.handle_utterance(s, text, conf, snr)


def test_start_greets_and_asks_first_field():
    eng, s, t = new()
    assert t["action"] == "ask" and "నమస్కారం" in t["say_te"] and "మీ పేరు" in t["say_te"]
    assert t["progress"] == {"index": 0, "total": 8}


def test_happy_path_full_form_adaptive():
    eng, s, _ = new()
    t = say(eng, s, "నా పేరు రాము")                # medium risk -> confirm
    assert t["action"] == "confirm" and t["confirm"]["display"] == "రాము"
    t = say(eng, s, "అవును")
    assert t["action"] == "ask" and s.fields["name"].status == "confirmed"
    say(eng, s, "అరవై రెండు"); say(eng, s, "అవును")
    say(eng, s, "గొల్లపాలెం"); say(eng, s, "అవును")
    say(eng, s, "విశాఖపట్నం"); say(eng, s, "అవును")
    t = say(eng, s, "9876543210")                  # critical -> digits read-back
    assert t["action"] == "confirm" and t["confirm"]["mode"] == "digits"
    assert "9 8 7, 6 5 4, 3 2 1 0" in t["say_te"]
    say(eng, s, "అవును")
    t = say(eng, s, "రెండున్నర ఎకరాలు")
    assert t["confirm"]["mode"] == "explicit"
    say(eng, s, "అవును")
    t = say(eng, s, "పత్తి")                       # low risk + clean -> implicit commit
    assert t["action"] == "ask" and s.fields["crop"].status == "implicit"
    t = say(eng, s, "ఉంది")
    assert t["action"] == "review" and s.state == "review"
    assert s.fields["land_acres"].value == 2.5 and s.fields["phone"].value == "9876543210"
    assert s.fields["has_bank"].value is True
    eng.finish(s)
    assert s.state == "done"


def test_wrong_value_caught_by_confirm():
    eng, s, _ = new()
    say(eng, s, "రాము"); say(eng, s, "అవును")
    t = say(eng, s, "ఇరవై ఐదు")                    # mis-heard (user said 26)
    assert t["action"] == "confirm"
    t = say(eng, s, "కాదు")
    assert t["action"] == "reask" and s.fields["age"].status == "empty"
    t = say(eng, s, "ఇరవై ఆరు")
    assert t["action"] == "confirm"
    say(eng, s, "అవును")
    assert s.fields["age"].value == 26


def test_invalid_then_fallback_after_two_failures():
    eng, s, _ = new()
    say(eng, s, "రాము"); say(eng, s, "అవును")
    t = say(eng, s, "హలో")
    assert t["action"] == "reask"
    t = say(eng, s, "హలో హలో")
    assert t["action"] == "fallback"
    t = eng.handle_typed(s, "30")
    assert t["action"] == "ask" and s.fields["age"].value == 30
    assert s.fields["age"].status == "needs_check" and s.fields["age"].source == "typed"


def test_typed_invalid_stays_in_fallback():
    eng, s, _ = new()
    t = eng.handle_typed(s, "")
    assert t["action"] == "fallback"


def test_back_repeat_skip():
    eng, s, _ = new()
    say(eng, s, "రాము"); say(eng, s, "అవును")
    assert s.idx == 1
    t = say(eng, s, "మళ్ళీ చెప్పండి")
    assert t["action"] == "ask" and s.idx == 1
    t = say(eng, s, "వెనక్కి")
    assert s.idx == 0 and s.fields["name"].status == "empty"
    say(eng, s, "రాము"); say(eng, s, "అవును")
    t = say(eng, s, "దాటవేయి")
    assert s.fields["age"].status == "skipped" and s.idx == 2


def test_unclear_confirm_answer_reprompts():
    eng, s, _ = new()
    say(eng, s, "రాము")
    t = say(eng, s, "హమ్మ్")
    assert t["action"] == "confirm" and s.state == "confirm"


def test_rejecting_twice_offers_typing():
    eng, s, _ = new()
    say(eng, s, "రాము"); say(eng, s, "కాదు")
    say(eng, s, "రాము"); t = say(eng, s, "కాదు")
    assert t["action"] == "fallback"


def test_empty_audio_reasks_then_falls_back():
    eng, s, _ = new()
    assert say(eng, s, "")["action"] == "reask"
    assert say(eng, s, "  ")["action"] == "fallback"


def test_review_edit_and_rerecord():
    eng, s, _ = new("never", "pension_scheme")        # 'never' policy: commit everything
    for text in ["రాము", "అరవై ఐదు", "గొల్లపాలెం", "9876543210", "లేదు"]:
        t = say(eng, s, text)
    assert t["action"] == "review"
    t = eng.edit_field(s, "age", "డెబ్బై")
    assert s.fields["age"].value == 70 and s.fields["age"].status == "edited"
    t = eng.edit_field(s, "age", "హలో")
    assert t.get("error") == "not_number" and s.fields["age"].value == 70
    t = eng.rerecord(s, "village")
    assert t["action"] == "ask" and s.state == "ask"
    t = say(eng, s, "విజయనగరం")
    assert t["action"] == "review" and s.fields["village"].display == "విజయనగరం"


def test_always_policy_confirms_everything_never_policy_nothing():
    eng, s, _ = new("always")
    s.idx = 6                                           # crop (low risk)
    assert say(eng, s, "పత్తి")["action"] == "confirm"
    eng, s, _ = new("never")
    s.idx = 4                                           # phone (critical)
    assert say(eng, s, "9876543210")["action"] == "ask"


def test_noise_and_low_confidence_raise_confirmation():
    eng, s, _ = new()
    s.idx = 6
    assert say(eng, s, "పత్తి", conf=0.95, snr=30)["action"] == "ask"       # implicit commit
    eng, s, _ = new()
    s.idx = 6
    assert say(eng, s, "పత్తి", conf=0.3, snr=30)["action"] == "confirm"    # low confidence
    eng, s, _ = new()
    s.idx = 6
    assert say(eng, s, "పత్తి", conf=0.8, snr=8)["action"] == "confirm"     # noisy audio


def test_session_store_expiry_and_delete():
    store = SessionStore(ttl_s=0)
    s = store.create(FORMS["farmer_scheme"])
    import time; time.sleep(0.01)
    assert store.get(s.id) is None
    store2 = SessionStore()
    s2 = store2.create(FORMS["farmer_scheme"])
    assert store2.delete(s2.id) and store2.get(s2.id) is None
