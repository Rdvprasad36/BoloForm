# Bolo Form: Design Document

Owner: RDV. Companion to PRD.md and ARCHITECTURE.md.

## 1. Design principles

1. **Audio first, screen second.** The user should be able to finish the form without reading. The screen mirrors what is spoken.
2. **One question at a time.** No scrolling forms, no tiny fields.
3. **Never silent.** Always show what was heard, before committing it.
4. **Never stuck.** Every voice step has a typed fallback and a visible "try again".
5. **Calm and respectful.** Slow pace, short Telugu sentences, no blame ("I didn't catch that", never "you said it wrong").
6. **Honest.** Show uncertainty ("I heard 62, is that right?"), and publish limits.

## 2. Screens

### S1. Welcome
- Logo, one sentence ("Speak in Telugu. I will fill the form."), language chip (తెలుగు selected).
- Form picker: Farmer Scheme (default), plus Pension and Health Camp if built.
- Toggle: **Phone-line mode** (simulates a phone call, off by default).
- Primary button: "Start / ప్రారంభించు".
- Footer link: Privacy and Limits. A short notice: "Demo only. Do not enter real personal data."
- On start, plays the greeting audio. Browsers block autoplay, so this button press is the user gesture that unlocks audio.

### S2. Question screen (the main screen)
Layout, top to bottom:
1. Progress: "3 of 8" plus a segmented bar (not color only; includes text).
2. Question card: Telugu question in large type (28–32 px), English gloss below in smaller grey text, replay button.
3. **Mic button**: 120 px circle, centered. States below.
4. Live transcript area: "మీరు చెప్పింది: ..." with the raw transcript.
5. Secondary row: "Type instead", "Skip", "Back".
6. Collapsed side panel (desktop) or bottom sheet (mobile): form so far.

Mic button states:

| State | Visual | Label (te / en) | Behavior |
|---|---|---|---|
| Idle | Teal, mic icon | నొక్కి చెప్పండి / Tap to speak | Tap or press Space to start |
| Listening | Saffron ring pulsing (static if reduced motion), live level meter | వింటున్నాను… / Listening | Tap again to stop; auto-stop after silence (about 1.5 s) or 12 s max |
| Processing | Spinner inside button | ఆలోచిస్తున్నాను… / Thinking | Disabled; shows a slow-response hint after 5 s |
| Speaking | Wave animation | చెబుతున్నాను… / Speaking | Tap to interrupt |
| Error | Red outline | మళ్ళీ ప్రయత్నించండి / Try again | Retry button |

### S3. Confirm card (inline over the question)
- Shows the parsed value in very large type, with the Telugu read-back text.
- Two big buttons: **అవును / Yes** (teal) and **కాదు / No** (outlined). Same words work by voice.
- For phone numbers: digits shown in groups of 2–3, each group highlighted as it is spoken.
- When confirm mode is "implicit" (low risk), no card is shown; the value slides into the side panel and a small "Undo" appears for 5 s.

### S4. Review screen
- Title: "Please check your form".
- List of fields: label, value, status chip (Confirmed / Edited / Skipped / Needs check).
- Each row is editable by tap (typed) or by a mic icon (voice re-record for that field).
- Button: "Read all aloud" and "Finish".
- Fields marked **Needs check** appear first, with a saffron badge (low confidence or typed fallback used).

### S5. Done
- "Your demo form is ready."
- Summary card, optional "Download PDF" (P2).
- **Privacy receipt (P2):** "No audio saved. Answers deleted when you close this page." plus a Delete now button.

### S6. Eval (`/eval`)
- Headline: silent-error rate by condition, in a small table and one bar chart.
- Tabs: Clean, Noisy (20 / 10 / 5 dB), Phone-line, Real speakers.
- Callout: "Synthetic speech is cleaner than real speech. See the real-speaker tab."
- Download buttons: `results.json`, `report.md`.

### S7. Limits (`/limits`)
- Plain list of measured failures, example transcripts (synthetic), what was fixed, what is still broken.
- Tone: factual, no marketing.

## 3. Interaction details

- **Barge-in:** tapping the mic while audio plays stops playback and starts recording.
- **Silence handling:** if no speech detected, say "I didn't hear anything" once, then show typed fallback after 2 tries.
- **Voice commands** are recognized before field parsing: repeat, back, skip (see ARCHITECTURE section 5).
- **Undo:** last committed field can be undone for 5 seconds.
- **Time-outs:** session expires after 10 minutes of inactivity and is purged; a notice is shown.
- **Offline or API failure:** show "Voice is not available, you can type" and continue with text.

## 4. Visual system

### Colors

| Token | Hex | Use |
|---|---|---|
| `--teal-700` | #0F766E | Primary, mic idle, headings |
| `--teal-50` | #E6F4F2 | Card backgrounds |
| `--saffron-500` | #F59E0B | Listening state, highlights, check mark |
| `--ink-900` | #0B1B2B | Text |
| `--ink-600` | #4B5B6B | Secondary text |
| `--paper` | #FAFAF7 | Page background |
| `--error` | #B42318 | Errors |
| `--ok` | #067647 | Confirmed |

Dark mode: swap to `--paper: #0E1620`, text `#E6EDF3`, keep teal and saffron, verify contrast.
Contrast target: WCAG AA (4.5:1 for text). **Do not rely on color alone** for state; always pair with text or icon.

### Typography
- Telugu: `"Noto Sans Telugu", "Nirmala UI", Gautami, sans-serif`
- Latin: `Inter, "Segoe UI", system-ui, sans-serif`
- Sizes: question 28–32 px, confirm value 40 px, body 18 px, minimum 16 px. Line height 1.5 for Telugu (taller glyphs).
- Telugu fonts are heavy, so subset or use system fallback if load time is high.

### Shape and spacing
- 8 px grid, cards 16–24 px radius, touch targets at least 56 px, mic button 120 px.
- One accent action per screen.

### Motion
- Subtle: pulse on listening, slide on commit. Respect `prefers-reduced-motion` (replace pulse with a static ring).

## 5. Copy deck (Telugu with English gloss)

> **All Telugu strings need review by a native speaker before recording the demo.** Treat them as drafts.

| Key | Telugu | English gloss |
|---|---|---|
| greeting | నమస్కారం! నేను మీ ఫారం నింపడంలో సహాయం చేస్తాను. మైక్ బటన్ నొక్కి చెప్పండి. | Hello! I will help fill your form. Tap the mic and speak. |
| q_name | మీ పేరు ఏమిటి? | What is your name? |
| q_age | మీ వయస్సు ఎంత? | How old are you? |
| q_village | మీ ఊరు పేరు ఏమిటి? | What is your village? |
| q_district | మీ జిల్లా ఏది? | Which district? |
| q_phone | మీ ఫోన్ నంబర్ చెప్పండి. | Tell me your phone number. |
| q_land | మీకు ఎన్ని ఎకరాల భూమి ఉంది? | How many acres of land do you have? |
| q_crop | మీరు ప్రధానంగా ఏ పంట వేస్తారు? | Which crop do you mainly grow? |
| q_bank | మీకు బ్యాంక్ ఖాతా ఉందా? | Do you have a bank account? |
| confirm | {value}. సరైనదేనా? | {value}. Is that correct? |
| yes | అవును | Yes |
| no | కాదు | No |
| repeat_cmd | మళ్ళీ చెప్పండి | Say again |
| back_cmd | వెనక్కి | Go back |
| skip_cmd | దాటవేయి | Skip |
| not_heard | క్షమించండి, నాకు వినిపించలేదు. మళ్ళీ చెప్పండి. | Sorry, I did not hear. Please say again. |
| invalid_phone | ఫోన్ నంబర్ పది అంకెలు ఉండాలి. మళ్ళీ చెప్పండి. | Phone number must be ten digits. Say again. |
| review | దయచేసి ఒకసారి చూసి సరిచూడండి. | Please check once. |
| done | మీ ఫారం సిద్ధంగా ఉంది. | Your form is ready. |

Style rules: short sentences, respectful register, numbers read in Telugu words for TTS, digits shown on screen. Avoid English words unless users commonly say them (for example "bank").

## 6. Accessibility checklist

- [ ] Every control has an accessible name; mic button has `aria-pressed` and `aria-label` that updates with state.
- [ ] Live regions (`aria-live="polite"`) announce transcript and errors.
- [ ] Space/Enter operates the mic; Esc cancels listening.
- [ ] Focus is moved to the confirm card when it appears.
- [ ] Text zoom to 200% works without breaking layout.
- [ ] State is conveyed by text and icon, not color alone.
- [ ] Tested on a phone-width viewport (360 px).

## 7. Demo video storyboard (60 s)

| Time | Shot | Voiceover / on screen |
|---|---|---|
| 0–8 | Phone screen with a long English form, a hand struggling | "This form takes my grandmother an hour, and she needs help to type." |
| 8–15 | Bolo Form welcome, logo | "Bolo Form fills it by voice, in Telugu." |
| 15–40 | Live Telugu fill. At the phone number, STT mishears a digit, read-back catches it, user says "కాదు", fixes it | "It reads every risky answer back. This is a caught error." |
| 40–52 | `/eval` page, results table | "I measured silent errors across clean, noisy and phone-line audio. Here are the real numbers, including the failures." |
| 52–60 | Logo, models | "Built on Gnani Prisma and Timbre. Bolo Form." |

Record in a quiet room first, then a second take with background noise if the result is good. Show captions in English for judges.
