"""Form definitions: a form is a YAML config, not code."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

FIELD_TYPES = {"text", "integer", "decimal", "phone", "choice", "yes_no"}
RISKS = {"low", "medium", "critical"}


@dataclass
class Choice:
    value: str
    te: str
    en: str
    aliases: list[str] = field(default_factory=list)


@dataclass
class FieldDef:
    key: str
    type: str
    risk: str
    label_te: str
    label_en: str
    prompt_te: str
    prompt_en: str
    min: float | None = None
    max: float | None = None
    choices: list[Choice] = field(default_factory=list)


@dataclass
class FormDef:
    id: str
    title_te: str
    title_en: str
    fields: list[FieldDef]

    def field_index(self, key: str) -> int:
        for i, f in enumerate(self.fields):
            if f.key == key:
                return i
        raise KeyError(key)


def _field(raw: dict) -> FieldDef:
    ftype, risk = raw["type"], raw.get("risk", "medium")
    if ftype not in FIELD_TYPES:
        raise ValueError(f"unknown field type {ftype!r} in field {raw.get('key')!r}")
    if risk not in RISKS:
        raise ValueError(f"unknown risk {risk!r} in field {raw.get('key')!r}")
    choices = [Choice(c["value"], c["te"], c["en"], [str(a) for a in c.get("aliases", [])])
               for c in raw.get("choices", [])]
    if ftype == "choice" and not choices:
        raise ValueError(f"choice field {raw['key']!r} needs choices")
    return FieldDef(key=raw["key"], type=ftype, risk=risk,
                    label_te=raw["label_te"], label_en=raw["label_en"],
                    prompt_te=raw["prompt_te"], prompt_en=raw["prompt_en"],
                    min=raw.get("min"), max=raw.get("max"), choices=choices)


def load_form(path: Path) -> FormDef:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    fields = [_field(f) for f in raw["fields"]]
    keys = [f.key for f in fields]
    if len(set(keys)) != len(keys):
        raise ValueError(f"duplicate field keys in {path.name}")
    return FormDef(id=raw["id"], title_te=raw["title_te"], title_en=raw["title_en"], fields=fields)


def load_forms(directory: Path) -> dict[str, FormDef]:
    forms: dict[str, FormDef] = {}
    for p in sorted(directory.glob("*.yaml")):
        f = load_form(p)
        forms[f.id] = f
    return forms
