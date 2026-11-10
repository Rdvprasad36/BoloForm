# Bolo Form — Project Explanation

## 1. Problem & Target Users
India has millions of citizens—particularly rural farmers, older individuals, and citizens with low literacy—who speak native regional languages (Telugu first). Yet, modern government subsidy schemes, bank applications, and agricultural enterprise forms exist overwhelmingly in English or complex bureaucratic language with complicated digital inputs.

Users often rely on third-party brokers who charge fees or make clerical errors. **Bolo Form** bridges this gap: a person speaks naturally in their native language (Telugu); Bolo Form interviews them voice-first, verifies critical and risky values via confirmation, and populates the host company's English form live via an embeddable widget.

---

## 2. What Was Built
1. **Dialogue Engine & Adaptive Confirmation Policy**:
   - Risk-adaptive confirmations: critical fields (phone numbers, land area) always trigger explicit or digit-by-digit readback confirmations.
   - Low-risk fields commit implicitly under clean conditions to minimize turn fatigue.
   - Robust retry and typed fallback logic for mishearings or audio failures.
2. **Embeddable Voice Widget (`embed.js` + `/widget`)**:
   - Single `<script>` tag drops into any existing HTML form.
   - Compact voice modal communicates with the parent page via bi-directional `postMessage`.
   - Populates host inputs (text, numbers, selects, checkboxes) using native setters without submitting the form automatically (user retains final control).
3. **Submissions & Inbox API**:
   - Creates structured submission records (`user_language="te"`, `company_language="en"`).
   - In-memory/SQLite store with auto-expiry (`SUBMISSION_TTL_HOURS`).
   - Tenant admin inbox at `/inbox` with CSV export protected against formula injection (DDE/Excel).
4. **Synthetic Degradation & Evaluation Harness**:
   - Evaluates performance across clean audio, synthetic pink noise (20, 10, 5 dB SNR), and simulated 8 kHz telephony conditions.

---

## 3. Gnani Models Used
- **Prisma (STT v2.5)**: Speech-to-Text transcription via `https://api.vachana.ai/stt/v3` (`model: "prisma-v2.5"`, `language_code: "te-IN"`, multipart 16 kHz mono WAV input).
- **Timbre (TTS v3.0)**: Text-to-Speech synthesis via `https://api.vachana.ai/api/v1/tts/inference` (`model: "timbre-v3.0"`, `voice: "Shivani"`, `language: "te-IN"`, returning 16 kHz mono WAV audio with RIFF container).

---

## 4. Architecture Summary
```
+-------------------------------------------------------------+
| Host Company Web Page (e.g. /demo/company.html)             |
|                                                             |
|  [English Form Inputs: Name, Age, Village, District, Phone]  |
|                                                             |
|  [ Fill by Voice / వాయిస్ ద్వారా నింపండి Button ]             |
|         |                                                   |
|         v (opens modal)                                     |
|  +-------------------------------------------------------+  |
|  | Bolo Form Widget Iframe (/widget)                     |  |
|  |                                                       |  |
|  | - Spoken Telugu Questions (Timbre TTS)                |  |
|  | - Microphone Capture (16 kHz WAV)                     |  |
|  | - Prisma STT Transcription                            |  |
|  | - Adaptive Readback Confirmation                      |  |
|  +-------------------------------------------------------+  |
|         |                                                   |
|         | window.parent.postMessage('bolo:field', ...)      |
|         v                                                   |
|  Native form inputs highlighted & populated live in English |
+-------------------------------------------------------------+
```

---

## 5. Measured Results (Only Real Measured Numbers)
All latency figures were measured directly on live network calls to `api.vachana.ai`:

- **TTS Latency (Timbre v3.0, n=8)**:
  - Median (p50): **2,238.7 ms** (~2.2 s)
  - 95th Percentile (p95): **3,681.9 ms** (~3.7 s)
  - Min: 1,472.3 ms, Max: 3,716.7 ms
- **STT Latency (Prisma v2.5, n=8)**:
  - Median (p50): **1,619.2 ms** (~1.6 s)
  - 95th Percentile (p95): **4,175.9 ms** (~4.2 s)
  - Min: 1,527.6 ms, Max: 5,424.2 ms
- **Combined Per-Turn Latency**:
  - Median (p50): **3,858.0 ms** (~3.9 s)
  - 95th Percentile (p95): **7,857.8 ms** (~7.9 s)

- **Test Suite**:
  - 85 unit and integration tests passing offline with zero network and no keys.

---

## 6. Known Limitations
1. **Turn Latency**: Roundtrip turn latency of ~3.9 seconds requires clear visual audio states ("Thinking...", "Speaking...") so users don't talk over prompts.
2. **Dialect Coverage**: Timbre synthetic voices and Prisma STT perform best on standard Telugu. Regional rustic dialects (e.g. rural Rayalaseema or Srikakulam vernaculars) can experience occasional mishearings on single-syllable crops or villages, making adaptive confirmation essential.
3. **Free Hosting Cold Starts**: On free container hosts (Render), idle services sleep and cold starts take ~40 seconds. In-memory session state resets on restart.

---

## 7. What's Next
- Direct WebSocket audio streaming for sub-second turn latency.
- Regional dialect acoustic adaptation for rural agricultural terminology.
- Multilingual expansion (Hindi, Tamil, Kannada) with community-reviewed native prompts.
