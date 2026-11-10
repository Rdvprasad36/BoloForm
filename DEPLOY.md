# Deployment Guide — Bolo Form on Render

This guide describes how to deploy **Bolo Form** on [Render](https://render.com) from GitHub with HTTPS.

---

## 1. Prerequisites
1. A GitHub account with access to `https://github.com/Rdvprasad36/BoloForm.git`.
2. A free [Render account](https://dashboard.render.com).

> [!IMPORTANT]
> **Microphone requires HTTPS.** Render automatically provisions free TLS/HTTPS certificates for all `*.onrender.com` domains. The browser microphone will only work over HTTPS (or on `localhost`).

---

## 2. Deploy Steps on Render

1. Log in to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** → **Web Service**.
3. Select **Build and deploy from a Git repository**.
4. Connect your GitHub repository `Rdvprasad36/BoloForm`.
5. Configure the service:
   - **Name**: `bolo-form` (or any chosen name)
   - **Region**: Singapore (`singapore`) or Frankfurt/Oregon
   - **Branch**: `main`
   - **Runtime**: **Docker** (Render will detect the `Dockerfile`)
   - **Instance Type**: **Free** (0.5 CPU, 512 MB RAM)
6. Add **Environment Variables** (see below).
7. Click **Create Web Service**.

Render will build the Docker container and start Uvicorn on `$PORT`.

---

## 3. Environment Variables to Set in Render Dashboard

In the **Environment** tab of your Render service, add the following key-value pairs:

| Variable | Recommended Production Value | Description |
|---|---|---|
| `PORT` | `10000` (Render sets automatically) | App listening port |
| `PROVIDER` | `gnani` (or `mock` for test mode) | Backend speech provider |
| `DEMO_CODE` | (e.g. `bolo2026`) | Access code protecting live voice credits |
| `MAX_LIVE_CALLS_PER_DAY` | `400` | Global daily cap to protect the 5,000 credit reserve |
| `CONFIRM_POLICY` | `adaptive` | Dialogue confirmation policy |
| `GNANI_API_KEY` | *(your secret Vachana API key)* | Never commit to Git |
| `GNANI_LANG_CODE` | `te-IN` | Telugu language code |
| `GNANI_STT_URL` | `https://api.vachana.ai/stt/v3` | Prisma STT endpoint |
| `GNANI_STT_AUTH` | `X-API-Key-ID: {key}` | STT Auth header template |
| `GNANI_STT_MODE` | `multipart` | Multipart file upload |
| `GNANI_STT_FILE_FIELD` | `audio_file` | Multipart field name |
| `GNANI_STT_FIELDS` | `{"language_code":"{lang}","model":"prisma-v2.5","format":"transcribe"}` | Extra STT payload |
| `GNANI_STT_TEXT_PATH` | `transcript` | JSON path to recognized text |
| `GNANI_TTS_URL` | `https://api.vachana.ai/api/v1/tts/inference` | Timbre TTS endpoint |
| `GNANI_TTS_AUTH` | `X-API-Key-ID: {key}` | TTS Auth header template |
| `GNANI_TTS_BODY` | `{"text":"{text}","model":"timbre-v3.0","voice":"{voice}","language":"{lang}","speed":1.0,"audio_config":{"sample_rate":16000,"num_channels":1,"sample_width":2,"encoding":"linear_pcm","container":"wav"}}` | TTS JSON payload |
| `GNANI_TTS_VOICE` | `Shivani` | Telugu female voice |
| `GNANI_TTS_RESPONSE` | `binary` | Returns WAV bytes directly |
| `GNANI_TTS_MIME` | `audio/wav` | Audio MIME type |

---

## 4. Honest Operational Limits & Warnings

1. **Free Tier Sleep/Spin-Down**:
   Render's free tier spins down instances after 15 minutes of inactivity. When a new visitor arrives, cold start may take 30–50 seconds.
2. **In-Memory State**:
   Sessions and submissions are kept in-memory (with 10-minute idle TTL) and will reset when the container restarts or spins down.
3. **Credit Protection**:
   - `DEMO_CODE`: If configured, live speech synthesis and transcription are only granted when the visitor enters the demo code. Otherwise, the app falls back to typed entry with an informative message.
   - Per-IP rate limiting: 30 turns per 10 minutes.
   - Daily cap: `MAX_LIVE_CALLS_PER_DAY` prevents surprise credit exhaustion.

---

## 5. Verification Checklist After Deploy

- [ ] Open `https://<your-app>.onrender.com/health` in browser — should return `{"ok": true, "provider": ...}`.
- [ ] Open `https://<your-app>.onrender.com` on a mobile phone (Chrome/Safari over HTTPS) — confirm microphone permission prompt appears and records cleanly.
- [ ] Test the Telugu voice flow: speak, confirm risky fields, inspect review screen, finish.
