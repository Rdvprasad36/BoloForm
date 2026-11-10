# -*- coding: utf-8 -*-
"""Scoring script for real-speaker evaluations (small sample)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from app.core.parsers import normalize

GROUND_TRUTH = {
    "speaker_1": {
        "name": "రాము",
        "age": 35,
        "village": "గొల్లపాలెం",
        "district": "visakhapatnam",
        "phone": "9876543210",
        "land_acres": 2.5,
        "crop": "paddy",
        "has_bank": True,
    },
    "speaker_2": {
        "name": "లక్ష్మి",
        "age": 42,
        "village": "కొత్తవలస",
        "district": "vizianagaram",
        "phone": "8765432109",
        "land_acres": 5.0,
        "crop": "chilli",
        "has_bank": False,
    },
    "speaker_3": {
        "name": "సత్యనారాయణ",
        "age": 58,
        "village": "తాటిపర్తి",
        "district": "kakinada",
        "phone": "7654321098",
        "land_acres": 3.5,
        "crop": "cotton",
        "has_bank": True,
    },
}


def score_transcripts(results: dict[str, dict[str, str]]) -> dict:
    total_fields = 0
    correct_fields = 0
    breakdown = {}

    for speaker_id, fields in results.items():
        truth = GROUND_TRUTH.get(speaker_id, {})
        breakdown[speaker_id] = {}
        for k, expected in truth.items():
            got = fields.get(k)
            total_fields += 1
            ok = normalize(str(expected)) == normalize(str(got)) if got is not None else False
            if ok:
                correct_fields += 1
            breakdown[speaker_id][k] = {"expected": expected, "got": got, "ok": ok}

    accuracy = correct_fields / max(1, total_fields)
    return {
        "total_fields": total_fields,
        "correct_fields": correct_fields,
        "field_accuracy": round(accuracy, 4),
        "details": breakdown,
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=None, help="Path to JSON file with speaker results")
    args = ap.parse_args()

    sample_results = {
        "speaker_1": {
            "name": "రాము", "age": "35", "village": "గొల్లపాలెం", "district": "visakhapatnam",
            "phone": "9876543210", "land_acres": "2.5", "crop": "paddy", "has_bank": "True"
        }
    }
    print("Scoring sample real-speaker transcript run:")
    res = score_transcripts(sample_results)
    print(json.dumps(res, ensure_ascii=False, indent=2))
