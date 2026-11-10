# -*- coding: utf-8 -*-
"""Turn a transcript into a typed, validated value."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher

from . import lexicon_te as L
from .forms import FieldDef


@dataclass
class ParseResult:
    ok: bool
    value: object = None
    display: str = ""        # shown on screen (and in English gloss)
    spoken_te: str = ""      # what Timbre should read back
    display_en: str = ""
    error: str = ""          # key into lexicon MSG when not ok
    ambiguous: bool = False


def fail(error: str) -> ParseResult:
    return ParseResult(ok=False, error=error)


# ---------------------------------------------------------------- normalize
def normalize(text: str) -> str:
    """NFC, lowercase, Telugu digits -> ASCII, punctuation -> space (keeps 2.5)."""
    text = unicodedata.normalize("NFC", text or "")
    out: list[str] = []
    chars = list(text)
    for i, ch in enumerate(chars):
        if ch in L.TELUGU_DIGITS:
            out.append(L.TELUGU_DIGITS[ch])
            continue
        cat = unicodedata.category(ch)
        if ch in "\u200c\u200d":          # ZWNJ / ZWJ
            continue
        if cat.startswith(("P", "S")) or cat in ("Cc", "Zs", "Zl", "Zp"):
            prev_d = i > 0 and (chars[i - 1].isdigit() or chars[i - 1] in L.TELUGU_DIGITS)
            next_d = i + 1 < len(chars) and (chars[i + 1].isdigit() or chars[i + 1] in L.TELUGU_DIGITS)
            if ch == "." and prev_d and next_d:
                out.append(".")
            else:
                out.append(" ")
            continue
        out.append(ch)
    return " ".join("".join(out).lower().split())


def tokens_of(text: str) -> list[str]:
    return normalize(text).split()


def _find_phrase(tokens: list[str], phrase: list[str]) -> bool:
    n = len(phrase)
    return any(tokens[i:i + n] == phrase for i in range(len(tokens) - n + 1))


def detect_command(text: str) -> str | None:
    toks = tokens_of(text)
    for name, phrases in (("repeat", L.REPEAT), ("back", L.BACK), ("skip", L.SKIP)):
        if any(_find_phrase(toks, p) for p in phrases):
            return name
    return None


# ---------------------------------------------------------------- numbers
def words_to_int(tokens: list[str]) -> int | None:
    """Parse Telugu/English number words and digit tokens ('ఇరవై ఐదు' -> 25)."""
    total, cur, seen = 0, 0, False
    for t in tokens:
        if t.isdigit():
            cur += int(t)
            seen = True
        elif t in L.UNITS:
            cur += L.UNITS[t]
            seen = True
        elif t in L.TEENS:
            cur += L.TEENS[t]
            seen = True
        elif t in L.TENS:
            cur += L.TENS[t]
            seen = True
        elif t in L.HUNDRED:
            cur = (cur or 1) * 100 if cur < 100 else cur
            seen = True
        elif t in L.THOUSAND:
            total += (cur or 1) * 1000
            cur = 0
            seen = True
        # unknown tokens (units, fillers) are ignored
    return total + cur if seen else None


def _fmt_number(x: float) -> str:
    return str(int(x)) if float(x).is_integer() else f"{x:.2f}".rstrip("0").rstrip(".")


def parse_integer(text: str, lo: float | None, hi: float | None) -> ParseResult:
    toks = [t for t in tokens_of(text) if t not in L.UNIT_WORDS]
    if not toks:
        return fail("empty")
    has_words = any(t in L.UNITS or t in L.TEENS or t in L.TENS or t in L.HUNDRED or t in L.THOUSAND
                    for t in toks)
    digit_runs = [t for t in toks if t.isdigit()]
    if digit_runs and not has_words:
        value: int | None = int(digit_runs[0])
    else:
        value = words_to_int(toks)
    if value is None:
        return fail("not_number")
    if (lo is not None and value < lo) or (hi is not None and value > hi):
        return fail("out_of_range")
    s = str(value)
    return ParseResult(True, value, s, s, s)


def parse_decimal(text: str, lo: float | None, hi: float | None) -> ParseResult:
    toks = [t for t in tokens_of(text) if t not in L.UNIT_WORDS]
    if not toks:
        return fail("empty")
    value: float | None = None
    for t in toks:
        if t in L.HALF_FORMS:
            value = L.HALF_FORMS[t]
            break
    if value is None:
        for t in toks:
            if re.fullmatch(r"\d+(?:\.\d+)?", t):
                value = float(t)
                break
    if value is None:
        pt = next((i for i, t in enumerate(toks) if t in L.POINT_WORDS), None)
        if pt is not None:
            left = words_to_int(toks[:pt])
            right_digits = []
            for t in toks[pt + 1:]:
                if t.isdigit():
                    right_digits.append(t)
                elif t in L.UNITS and L.UNITS[t] <= 9:
                    right_digits.append(str(L.UNITS[t]))
            if left is not None and right_digits:
                value = float(f"{left}.{''.join(right_digits)}")
    if value is None:
        n = words_to_int(toks)
        value = float(n) if n is not None else None
    if value is None:
        return fail("not_number")
    value = round(value, 2)
    if (lo is not None and value < lo) or (hi is not None and value > hi):
        return fail("out_of_range")
    s = _fmt_number(value)
    return ParseResult(True, value, s, s, s)


# ---------------------------------------------------------------- phone
def phone_groups(d: str) -> str:
    return f"{d[:5]} {d[5:]}" if len(d) == 10 else d


def phone_spoken(d: str) -> str:
    """Digit by digit with pauses (commas): 9 8 7, 6 5 4, 3 2 1 0."""
    if len(d) != 10:
        return " ".join(d)
    parts = [d[:3], d[3:6], d[6:]]
    return ", ".join(" ".join(p) for p in parts)


def parse_phone(text: str) -> ParseResult:
    toks = tokens_of(text)
    if not toks:
        return fail("empty")
    digits: list[str] = []
    mult = 1
    for t in toks:
        if t in L.DOUBLE_WORDS:
            mult = 2
            continue
        if t in L.TRIPLE_WORDS:
            mult = 3
            continue
        if t.isdigit():
            digits.append(t * mult if len(t) == 1 else t)
            mult = 1
        elif t in L.UNITS and L.UNITS[t] <= 9 and t not in ("ఒక",):
            digits.append(str(L.UNITS[t]) * mult)
            mult = 1
    d = "".join(digits)
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    elif len(d) == 11 and d.startswith("0"):
        d = d[1:]
    if len(d) != 10:
        return fail("not_10_digits")
    if d[0] not in "6789":
        return fail("bad_start")
    return ParseResult(True, d, phone_groups(d), phone_spoken(d), phone_groups(d))


# ---------------------------------------------------------------- yes / no
def parse_yes_no_raw(text: str) -> bool | None:
    toks = set(tokens_of(text))
    y, n = bool(toks & L.YES), bool(toks & L.NO)
    if y == n:
        return None
    return y


def parse_yes_no(text: str) -> ParseResult:
    r = parse_yes_no_raw(text)
    if r is None:
        return fail("no_match")
    return ParseResult(True, r, L.YES_TE if r else L.NO_TE, L.YES_TE if r else L.NO_TE,
                       "Yes" if r else "No")


# ---------------------------------------------------------------- choice
def _alias_list(c) -> list[str]:
    raw = [c.value.replace("_", " "), c.te, c.en, *c.aliases]
    return [a for a in (normalize(x) for x in raw) if a]


def parse_choice(text: str, f: FieldDef) -> ParseResult:
    norm = normalize(text)
    if not norm:
        return fail("empty")
    toks = norm.split()
    scores: list[tuple[float, object]] = []
    for c in f.choices:
        best = 0.0
        for alias in _alias_list(c):
            a_toks = alias.split()
            if _find_phrase(toks, a_toks):
                best = max(best, 100.0 + len(alias) / 100)      # longest exact alias wins ties
                continue
            best = max(best, SequenceMatcher(None, alias, norm).ratio() * 100)
            for t in toks:
                best = max(best, SequenceMatcher(None, alias, t).ratio() * 100)
        scores.append((best, c))
    scores.sort(key=lambda x: x[0], reverse=True)
    top_score, top = scores[0]
    if top_score < 75:
        return fail("no_match")
    ambiguous = len(scores) > 1 and top_score < 100 and (top_score - scores[1][0]) < 8
    return ParseResult(True, top.value, top.te, top.te, top.en, ambiguous=ambiguous)


# ---------------------------------------------------------------- free text
def parse_text(text: str) -> ParseResult:
    toks = [t for t in tokens_of(text) if t not in L.FILLERS]
    if not toks:
        return fail("empty")
    s = " ".join(toks)
    if s.isascii():
        s = s.title()
    if len(s) < 2 or len(s) > 60:
        return fail("no_match")
    return ParseResult(True, s, s, s, s)


# ---------------------------------------------------------------- dispatcher
def parse_field(f: FieldDef, text: str) -> ParseResult:
    if f.type == "integer":
        return parse_integer(text, f.min, f.max)
    if f.type == "decimal":
        return parse_decimal(text, f.min, f.max)
    if f.type == "phone":
        return parse_phone(text)
    if f.type == "choice":
        return parse_choice(text, f)
    if f.type == "yes_no":
        return parse_yes_no(text)
    return parse_text(text)
