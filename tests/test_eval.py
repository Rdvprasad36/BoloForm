# -*- coding: utf-8 -*-
import json, tempfile
from eval import run_eval as E
from app.core import lexicon_te as L
from app.core.parsers import parse_integer


def test_int_to_te_roundtrips_through_parser():
    for n in list(range(1, 100)):
        r = parse_integer(E.int_to_te(n), 1, 99)
        assert r.ok and r.value == n, (n, E.int_to_te(n), r)


def test_personas_are_seeded_and_fake():
    from pathlib import Path
    from app.core.forms import load_forms
    form = load_forms(Path(E.ROOT) / "app" / "forms")["farmer_scheme"]
    a, b = E.build_personas(form, 10, 7), E.build_personas(form, 10, 7)
    assert [p.truth for p in a] == [p.truth for p in b]
    assert all(len(p.truth["phone"]) == 10 and p.truth["phone"][0] in "6789" for p in a)


def test_wilson_bounds():
    lo, hi = E.wilson(0, 480)
    assert lo == 0.0 and 0 < hi < 0.02
    assert E.wilson(0, 0) == [0.0, 0.0]


def test_eval_on_mock_is_marked_simulated_and_confirmation_beats_none():
    out = tempfile.mkdtemp()
    assert E.main(["--provider", "mock", "--n", "40", "--split", "all", "--conditions", "clean,noise5",
                   "--out", out]) == 0
    d = json.load(open(out + "/results.json", encoding="utf-8"))
    assert d["meta"]["simulated"] is True
    noisy = d["results"]["noise5"]
    assert noisy["never_confirm"]["silent_error_rate"] > noisy["always_confirm"]["silent_error_rate"]
    assert noisy["adaptive"]["silent_error_rate"] <= noisy["never_confirm"]["silent_error_rate"]
    assert noisy["adaptive"]["confirms_per_form"] <= noisy["always_confirm"]["confirms_per_form"]
    assert "SIMULATED" in open(out + "/report.md", encoding="utf-8").read()


def test_dry_run_makes_no_calls():
    assert E.main(["--provider", "gnani", "--n", "400", "--dry-run"]) == 0


def test_live_run_refuses_over_budget_before_touching_the_network():
    assert E.main(["--provider", "gnani", "--n", "400", "--max-calls", "10"]) == 2
