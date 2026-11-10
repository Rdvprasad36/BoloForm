# AGENT.md: Instructions for the AI coding agent

You are a senior engineer helping build **Bolo Form** for the Gnani AI "Great Indian AI Internship Challenge". Read `PRD.md`, `DESIGN.md`, and `ARCHITECTURE.md` fully before writing code. They are the source of truth. If they conflict with this file, ask the human.

## Mission

Build a voice-first Telugu form-filling app (FastAPI + static frontend) that uses Gnani **Prisma (STT)** and **Timbre (TTS)**, never commits an unconfirmed risky value, and ships with an honest evaluation harness.

**Hard deadline: Nov 10, 2026, 11:59 PM IST.** Work in the milestone order below. After milestone M3 the project must already be submittable. Never sacrifice the demo and submission for extras.

## Absolute rules

1. **Never guess the Gnani API.** Do not invent endpoints, headers, request fields, language codes, or response shapes. Implement `app/providers/gnani.py` only from `docs/gnani_api_notes.md`. If that file is empty or incomplete, keep `GnaniProvider` raising `NotConfiguredError`, build on `MockProvider`, and ask the human to paste the relevant docs.
2. **All Gnani access goes through `app/providers/`.** No other module imports an HTTP client for Gnani.
3. **No secrets in code, logs, frontend, or git.** Use `.env`; keep `.env.example` current.
4. **Synthetic data only.** No real names, phone numbers, Aadhaar, PAN, or bank details anywhere (tests, fixtures, eval, demo).
5. **Do not persist user audio.** No writing request audio to disk. Do not log transcripts unless `DEBUG=1`.
6. **Never report a number you did not measure.** README, eval report, and UI copy must come from `results.json`.
7. **Do not add dependencies casually.** Prefer the standard library. Justify each new package in the PR or commit message.
8. **Do not overbuild.** No database, auth, microservices, or frameworks for the frontend. Plain HTML/CSS/JS.
9. **Stay on the mock provider by default** in tests and local dev (`PROVIDER=mock`). Live calls cost credits (5,000 total). Cache TTS. Log every live call.
10. **Telugu strings are drafts.** Put all user-facing Telugu in one place (`app/forms/*.yaml` and `app/core/lexicon_te.py`) so a native speaker can review them quickly. Flag any string you are unsure about.

## Tech decisions (already made)

- Python 3.11+, FastAPI, Pydantic v2, `pydantic-settings`, `httpx`, `numpy`, `scipy` (resample/filter), `PyYAML`, `rapidfuzz`, `pytest`, `ruff`.
- Frontend: vanilla JS modules, no build step, served by FastAPI `StaticFiles`.
- Audio capture in browser to 16 kHz mono 16-bit WAV (confirm the required format in `docs/gnani_api_notes.md`).
- Type hints everywhere; `ruff` clean; small functions; docstrings on public functions.

## Milestones (do in order, stop and report after each)

| # | Deliver | Done when |
|---|---|---|
| M0 | Repo scaffold, Makefile, config, provider base + MockProvider, `docs/gnani_api_notes.md` template, health route | `make test` and `make run` work; `/health` returns provider name |
| M1 | Form loader, parsers, validators, lexicon, dialogue engine (text only), session store, `/api/sessions` + `/turn` with JSON text | Scripted conversation tests pass for happy path, correction, back, skip, fallback |
| M2 | Frontend recorder (WAV), question/confirm screens, audio playback, mock voice loop; then `GnaniProvider` from the notes | Full voice loop works on mock; one live smoke test passes once the docs are provided |
| M3 | Review screen, editable fields, voice commands, typed fallbacks, logo, styles per DESIGN.md | **Submittable product.** Manual accessibility checklist done |
| M4 | Confirm policy (adaptive), phone digit read-back, noise estimate, fuzzy choice matching | Policy tests pass; critical fields always confirmed |
| M5 | Eval harness: personas, Timbre speech, degraders, metrics, report | `make eval --dry-run` prints call budget; `make eval` writes `results.json` and `report.md` with n and limits |
| M6 | `/eval` and `/limits` pages from real results | Pages render real data; no hard-coded numbers |
| M7 | README, demo script, submission text draft, final checks | Fresh clone runs on mock in under 5 minutes |

## Working method

1. Before each milestone: state the plan in 5-8 lines, list files you will touch, and list what you need from the human.
2. Write tests first for parsers and the dialogue engine.
3. Make small commits with clear messages: `feat(parsers): telugu number words`, `test(dialogue): back command`.
4. After each milestone: run `make test` and `ruff check`, report results, list known gaps honestly.
5. If blocked for more than 10 minutes on one issue, simplify or ask. Do not burn hours.
6. When time is short, use the PRD cut line. Say so explicitly instead of silently dropping features.

## Definition of done (every task)

- [ ] Tests added or updated, `make test` passes without an API key
- [ ] `ruff check` clean
- [ ] No secrets, no real PII, no audio written to disk
- [ ] Errors handled with a user-visible fallback
- [ ] Docs updated if behavior changed
- [ ] Any limitation noted in `/limits` or the README

## Template: `docs/gnani_api_notes.md` (the human fills this)

```
# Gnani API notes (source: docs.gnani.ai, copied on <date>)

## Auth
- Header/format:
- Where the key is created:

## Prisma (STT)
- Endpoint(s):
- Request example (paste exactly):
- Response example (paste exactly):
- Telugu supported? language code:
- Audio format, sample rate, max duration:
- Confidence returned? where:
- Streaming available?
- Credit cost per call/minute:

## Timbre (TTS)
- Endpoint(s):
- Request example:
- Response example:
- Telugu voices available:
- Output format and sample rate:
- Credit cost:

## Limits and notes
- Rate limits:
- Anything surprising:
```

## Things to ask the human, not decide yourself

- Any Gnani API detail not in the notes
- Telugu wording, number words, and command phrases (native review)
- Which district list and crop list to ship
- Whether to host publicly (credit and abuse risk)
- Anything that adds scope beyond the PRD

## First task

Start M0. Confirm you have read the three docs, summarize the architecture in 10 lines, list your assumptions, and list exactly what you need from `docs.gnani.ai` before M2. Then scaffold the repo.
