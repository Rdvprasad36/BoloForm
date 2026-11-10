# -*- coding: utf-8 -*-
from pathlib import Path
from app.core.forms import load_forms
from app.core import parsers as P

FORMS = load_forms(Path(__file__).resolve().parent.parent / "app" / "forms")
FARM = FORMS["farmer_scheme"]
F = {f.key: f for f in FARM.fields}


def test_normalize_keeps_decimal_and_telugu_marks():
    assert P.normalize("౨.౫ ఎకరాలు!") == "2.5 ఎకరాలు"
    assert P.normalize("ఇరవై, ఐదు.") == "ఇరవై ఐదు"


def test_integer_digits_and_words():
    cases = {"25": 25, "నా వయస్సు 62": 62, "ఇరవై ఐదు": 25, "అరవై రెండు": 62, "యాభై": 50,
             "ముప్పై ఐదు సంవత్సరాలు": 35, "twenty five": 25, "౩౦": 30, "డెబ్బై": 70}
    for text, want in cases.items():
        r = P.parse_integer(text, 18, 100)
        assert r.ok and r.value == want, (text, r)


def test_integer_rejects_bad_input():
    assert P.parse_integer("పదిహేడు", 18, 100).error == "out_of_range"
    assert P.parse_integer("నూట ఇరవై", 18, 100).error == "out_of_range"
    assert P.parse_integer("హలో", 18, 100).error == "not_number"
    assert P.parse_integer("", 18, 100).error == "empty"


def test_number_words_hundreds_thousands():
    assert P.words_to_int(["నూట", "ఇరవై"]) == 120
    assert P.words_to_int(["రెండు", "వందల", "యాభై"]) == 250
    assert P.words_to_int(["మూడు", "వేలు"]) == 3000
    assert P.words_to_int(["ఇరవై", "ఐదు", "వేలు", "మూడు", "వందలు"]) == 25300


def test_decimal():
    cases = {"2.5": 2.5, "రెండున్నర ఎకరాలు": 2.5, "అర ఎకరం": 0.5, "మూడు ఎకరాలు": 3.0,
             "రెండు పాయింట్ ఐదు": 2.5, "10": 10.0, "పావు": 0.25}
    for text, want in cases.items():
        r = P.parse_decimal(text, 0.1, 500)
        assert r.ok and r.value == want, (text, r)
    assert P.parse_decimal("1000", 0.1, 500).error == "out_of_range"
    assert P.parse_decimal("0", 0.1, 500).error == "out_of_range"


def test_phone_ok():
    cases = {"9876543210": "9876543210", "98765 43210": "9876543210",
             "+91 98765 43210": "9876543210", "919876543210": "9876543210",
             "తొమ్మిది ఎనిమిది ఏడు ఆరు ఐదు నాలుగు మూడు రెండు ఒకటి సున్నా": "9876543210",
             "nine eight seven six five four three two one zero": "9876543210",
             "double nine eight seven six five four three two one": "9987654321"}
    for text, want in cases.items():
        r = P.parse_phone(text)
        assert r.ok and r.value == want, (text, r)
    assert P.parse_phone("9876543210").spoken_te == "9 8 7, 6 5 4, 3 2 1 0"


def test_phone_errors():
    assert P.parse_phone("98765 4321").error == "not_10_digits"
    assert P.parse_phone("1234567890").error == "bad_start"
    assert P.parse_phone("").error == "empty"


def test_yes_no():
    for t in ["అవును", "yes", "అవును సరైనదే", "సరే"]:
        assert P.parse_yes_no_raw(t) is True, t
    for t in ["కాదు", "no", "లేదు", "తప్పు"]:
        assert P.parse_yes_no_raw(t) is False, t
    assert P.parse_yes_no_raw("అవును కాదు") is None
    assert P.parse_yes_no_raw("బ్యాంక్") is None


def test_choice_exact_alias_and_fuzzy():
    r = P.parse_choice("మా జిల్లా విశాఖపట్నం", F["district"])
    assert r.ok and r.value == "visakhapatnam"
    assert P.parse_choice("vizag", F["district"]).value == "visakhapatnam"
    assert P.parse_choice("guntoor", F["district"]).value == "guntur"
    assert P.parse_choice("తూర్పు గోదావరి", F["district"]).value == "east_godavari"
    assert P.parse_choice("పశ్చిమ గోదావరి", F["district"]).value == "west_godavari"
    assert P.parse_choice("పత్తి", F["crop"]).value == "cotton"
    assert P.parse_choice("మిర్చి", F["crop"]).value == "chilli"
    assert not P.parse_choice("xyzqq", F["district"]).ok


def test_text_strips_fillers():
    assert P.parse_text("నా పేరు రాము").value == "రాము"
    assert P.parse_text("my name is lakshmi devi").value == "Lakshmi Devi"
    assert P.parse_text("").error == "empty"
    assert P.parse_text("నా పేరు").error == "empty"


def test_commands_whole_word_only():
    assert P.detect_command("మళ్ళీ చెప్పండి") == "repeat"
    assert P.detect_command("వెనక్కి") == "back"
    assert P.detect_command("skip") == "skip"
    assert P.detect_command("రాము") is None
    assert P.detect_command("nobody") is None


def test_every_form_loads_and_fields_valid():
    assert {"farmer_scheme", "pension_scheme"} <= set(FORMS)
    assert [f.key for f in FARM.fields] == ["name", "age", "village", "district", "phone",
                                           "land_acres", "crop", "has_bank"]
