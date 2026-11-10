# Bolo Form: Product Requirements Document

**Version:** 1.0  **Owner:** Durga Venkata Prasad Rapeti (RDV)
**Context:** Great Indian AI Internship Challenge (Gnani AI), solo entry
**Deadline:** Nov 10, 2026, 11:59 PM IST (hard, no extensions). Target submission: at least 1 hour earlier.

---

## 1. One-line summary

Bolo Form lets a person fill a long form **by talking in Telugu**. It asks each question aloud, listens, checks the answer, reads it back, and only commits what the person confirms. It also ships with a **built-in evaluation harness** that measures how often voice form-filling goes wrong, and where.

## 2. Problem

Many people in India cannot comfortably fill online forms: older people, first-time applicants, farmers, people with low typing or reading skill. Forms are long, in English or formal language, and a single mistake can mean a rejected application.

Voice seems like the obvious fix, but two things stop it from being trustworthy:

1. **Speech recognition errors on numbers and names** (phone digits, land area, age) are silent. The wrong value goes into the form and nobody notices.
2. **Nobody measures it.** Most voice demos show one clean success and no failure rate, especially for Telugu, dialects, or noisy and phone-quality audio.

## 3. Users

**Primary persona (fictional):** *Lakshmamma, 62, farmer, Anakapalli district.* Speaks Telugu, reads slowly, has a basic phone, nervous about forms, usually depends on a relative or a middleman.

**Secondary personas:**
- A first-time applicant who finds formal Telugu or English confusing.
- A helper (volunteer, CSC operator, family member) who fills forms for others and wants a faster, checked flow.

**Evaluator persona:** A Gnani engineer or hiring manager who wants to see Gnani models used well, honest measurement, and clean engineering.

## 4. Goals and non-goals

**Goals**
- G1. A complete voice-only path from the first question to a reviewed form, in Telugu.
- G2. No silent errors: every committed value is either confirmed or clearly flagged.
- G3. Show measured results (accuracy, errors caught, turns, latency) on clean, noisy, and telephone-quality audio.
- G4. Reusable: a new form is a config file, not new code.
- G5. Privacy-respecting: no audio stored, no real personal data.

**Non-goals**
- Real government integration, real submission, real Aadhaar, bank, or phone data.
- Live telephony or IVR (design notes only).
- User accounts, login, a database.
- Training or fine-tuning any model.

## 5. What makes this more than a demo

| # | Differentiator | Why it matters |
|---|---|---|
| D1 | **Risk-adaptive confirmation.** Confirm harder for risky fields (phone, amounts) and noisy audio, lighter for safe ones. | Cuts annoying repetition without raising error risk. |
| D2 | **Built-in eval harness** that uses Timbre to generate test speech, degrades it (noise, 8 kHz telephone band), runs it through Prisma, and scores the full dialogue. | Uses both Gnani models, produces real numbers, matches the Noise Canceller theme. |
| D3 | **Silent-error rate as the headline metric**, tuned on a dev split and reported on a held-out split. | Shows scientific discipline, not a cherry-picked demo. |
| D4 | **Form-as-config (YAML).** Farmer scheme, pension, and health camp ship as three configs. | Shows a platform, not a one-off. |
| D5 | **Telugu number and code-mixed handling**, with fuzzy matching on district and crop names and phone read-back in digit groups. | Solves the real failure point. |
| D6 | **Public "Limits" page** listing measured failures. | Honesty is a stated judging preference. |

## 6. User stories

- As Lakshmamma, I want the form to ask me questions in Telugu so I don't have to read or type.
- As Lakshmamma, I want it to repeat what I said so I know it understood me.
- As Lakshmamma, I want to say "మళ్ళీ చెప్పండి" (say again) or "వెనక్కి" (go back) without pressing anything else.
- As a helper, I want to see all answers on one screen at the end and fix any by tapping.
- As an evaluator, I want to see how accurate the system is, and where it fails, with numbers.

## 7. Functional requirements

### P0: must ship (the core)

| ID | Requirement |
|---|---|
| FR-1 | Forms are defined in YAML: fields with key, type, Telugu and English prompts, validation, risk level, choices and aliases. |
| FR-2 | Starting a session returns a spoken greeting and the first question (audio + text). |
| FR-3 | Browser records mic audio and converts it to 16 kHz mono WAV before upload. |
| FR-4 | Speech is transcribed via **Prisma** through the provider adapter (default language `te`). |
| FR-5 | Transcript is normalized and parsed per field type: `text`, `integer`, `decimal`, `phone`, `choice`, `yes_no`. |
| FR-6 | Invalid answers are re-asked with a short reason; after 2 failures a typed fallback appears. |
| FR-7 | Parsed value is read back with **Timbre** and the person answers yes or no by voice (or taps). |
| FR-8 | Voice commands: repeat, back, skip (Telugu and common English). |
| FR-9 | Review screen shows all fields, each editable, with a "read all aloud" button. |
| FR-10 | A **mock provider** works offline so development and tests never depend on the network or credits. |
| FR-11 | No audio is persisted. Sessions live in memory and are purged on completion, delete, or timeout. |

### P1: should ship (what wins the internship)

| ID | Requirement |
|---|---|
| FR-12 | Risk-adaptive confirmation policy (see ARCHITECTURE section 6). |
| FR-13 | Phone numbers read back in digit groups with pauses (for example 98 76 54 32 10). |
| FR-14 | "Phone-line mode" toggle: degrades audio to 8 kHz, 300–3400 Hz, µ-law before STT, to simulate a call. |
| FR-15 | Eval CLI: generates personas, TTS speech, degradations, runs the dialogue, writes `results.json` and `report.md`. |
| FR-16 | `/eval` page showing results, and `/limits` page listing measured failures. |
| FR-17 | Telugu number words, code-mixed digits, fuzzy match on district and crop names. |

### P2: nice to have (only if time is left)

| ID | Requirement |
|---|---|
| FR-18 | Pension and health camp form configs. |
| FR-19 | "Privacy receipt" screen after submission. |
| FR-20 | PDF export of the filled summary. |
| FR-21 | Hindi UI and prompts using the same schema. |

## 8. Non-functional requirements

- **Latency:** target under 3 s per turn on a normal connection (report p50 and p95, do not claim it before measuring).
- **Reliability:** every voice step has a visible, typed fallback.
- **Accessibility:** large touch targets, high contrast, screen-reader labels, keyboard control, reduced motion respected.
- **Privacy:** synthetic data only, no audio saved, no keys in the frontend, logs redact transcripts by default.
- **Portability:** runs locally with `make run`; optional Docker.
- **Provider swap:** all Gnani calls live behind one adapter so the app runs on the mock provider.

## 9. Success metrics

Reported on a held-out test split, and separately for clean, noisy, and phone-line conditions.

| Metric | Definition |
|---|---|
| First-pass field accuracy | Field correct on first transcription and parse |
| Final field accuracy | Committed value equals ground truth after confirm loop |
| **Silent-error rate** | Wrong value committed with no flag raised to the user (headline) |
| Errors caught by confirm | Wrong transcriptions caught by read-back |
| Turns per form | Total dialogue turns to complete 8 fields |
| Confirmation savings | Turns saved by adaptive policy vs always-confirm |
| Turn latency (p50 / p95) | Audio-in to audio-out |
| Fallback rate | Fields that needed typed fallback |

Targets are goals to aim for, not results. Never write a number in the README or the post that was not measured.

## 10. Time-box and cut line

The deadline is **tonight, Nov 10, 11:59 PM IST**. Check the clock and work back from it.

| Milestone | What | Budget |
|---|---|---|
| M0 | Repo, mock provider, one real STT and TTS call confirmed | 1.5 h |
| M1 | P0 dialogue loop works in text (no audio) | 2 h |
| M2 | Browser recording, WAV conversion, full voice loop on mock then Gnani | 2.5 h |
| M3 | Review screen, voice commands, fallbacks, logo, polish | 1.5 h |
| **CUT LINE** | **Everything above is a submittable product. Do not skip the demo video and the submission, even if later items fail.** | |
| M4 | Adaptive confirmation, phone digits, lexicon | 2 h |
| M5 | Eval harness with TTS-generated speech and degradations | 2.5 h |
| M6 | `/eval` and `/limits` pages | 1 h |
| M7 | Demo video, README, submission text, social posts, submit | 3 h |

If time is short: drop M6 first, then simplify M5 to clean vs telephone only. Never drop M7.

## 11. Challenge compliance

**Must do**
- [ ] Use at least one Gnani model (Prisma, Timbre) and **name each** in the submission.
- [ ] Synthetic or self-recorded consenting voices only; no real PII.
- [ ] Post demo on LinkedIn or X with `#GreatIndianAIInternshipChallenge` and `#GnaniAI`, and nominate the posts.
- [ ] Upload demo or video, written explanation, models list, post links.
- [ ] Read the programme terms (ownership) on the registration page.
- [ ] No purchased engagement.
- [ ] Be honest about limits in the demo.

**Award map (only one can be won):** Real Deal, Main Character, Small Town Big Build (Visakhapatnam), Solo Ninja, Noise Canceller (via phone-line mode and eval), Demo Day Drop (60-second video).

## 12. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Telugu not supported or weak in Prisma | Check docs first; fall back to Hindi/Hinglish using the same schema |
| Gnani API format unknown | Adapter + mock; never guess the endpoints (see AGENT.md) |
| Credits run out (5,000) | Cache TTS prompts; eval harness limited to a fixed small set; log credit use |
| Browser audio format mismatch | Convert to WAV in-browser; ffmpeg as server fallback |
| TTS speech is cleaner than human speech | Label eval as synthetic; add a small real-human set and report separately |
| Time runs out | Cut line in section 10 |
| Telugu prompts sound wrong | Ask a native speaker to review all prompt strings before recording |
| Eval overfit | Tune on dev split only, report on held-out split |

## 13. Open questions (answer from docs.gnani.ai or Discord)

1. Does Prisma accept Telugu, and what is the language code?
2. Accepted audio format, sample rate, max duration?
3. Does STT return word or utterance confidence?
4. Is there a streaming API, or only request/response?
5. Which Telugu voices does Timbre offer, and the output format?
6. How are credits charged for STT and TTS?
7. Can one participant submit more than one project? (Plan for one.)

## 14. Submission deliverables

- [ ] Working demo link or recorded demo, plus public GitHub repo
- [ ] 60-second demo video (problem, live Telugu fill with one error caught, results, models used)
- [ ] Written explanation: problem, users, models used, what was built, results, limits, next steps
- [ ] README with setup steps and the eval report
- [ ] LinkedIn/X post with both hashtags, nominated
- [ ] Final check of every link, then submit before 10:30 PM IST

## 15. Acceptance criteria for "done"

1. A tester who does not read Telugu can see the flow work from the transcript and English gloss shown on screen.
2. A Telugu speaker fills the 8-field farmer form by voice in under 3 minutes.
3. At least one deliberate misrecognition is caught by read-back in the demo.
4. All tests pass on the mock provider; at least one live Gnani smoke test passes.
5. README contains the measured table, including failures.
