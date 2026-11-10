# Gnani (Vachana) API notes
Source: docs.gnani.ai / api.vachana.ai (v2.5 / v3.0 REST APIs)

Copied on: Nov 10, 2026

## Auth
- Header name and format: `X-API-Key-ID: {key}`
- Where the key is created: Vachana / Gnani dashboard
- .env:
  `GNANI_API_KEY=<key>`
  `GNANI_STT_AUTH=X-API-Key-ID: {key}`
  `GNANI_TTS_AUTH=X-API-Key-ID: {key}`

## Prisma (STT v2.5 / v3 endpoint)
- Endpoint URL -> `GNANI_STT_URL`: `https://api.vachana.ai/stt/v3`
- Request style: multipart file upload (`GNANI_STT_MODE=multipart`)
- Name of the file field -> `GNANI_STT_FILE_FIELD`: `audio_file`
- Extra fields -> `GNANI_STT_FIELDS`: `{"language_code":"{lang}","model":"prisma-v2.5","format":"transcribe"}`
- Telugu supported? language code -> `GNANI_LANG_CODE`: `te-IN`
- Audio format: 16 kHz mono 16-bit WAV supported (also MP3, FLAC, OGG). Max duration: 30s.
- Response format:
```json
{
  "request_id": "req_...",
  "status": "success",
  "model": "prisma-v2.5",
  "language_code": "te-IN",
  "transcript": "...",
  "confidence": 0.98,
  "words": [...]
}
```
- Path to the transcript in response -> `GNANI_STT_TEXT_PATH`: `transcript`
- Confidence path -> `GNANI_STT_CONF_PATH`: `confidence`

## Timbre (TTS v3.0 / v2.5)
- Endpoint URL -> `GNANI_TTS_URL`: `https://api.vachana.ai/api/v1/tts/inference`
- Request style: JSON POST (`application/json`)
- JSON body shape -> `GNANI_TTS_BODY`: `{"text":"{text}","model":"timbre-v3.0","voice":"{voice}","language":"{lang}","speed":1.0}`
- Telugu voices available: `Shivani` (female), `Avinash` (male)
- Response: audio bytes (WAV/MP3) or base64 JSON
- MIME: `audio/wav` or `audio/mpeg`

## Smoke test
```python
import os
from app.providers.gnani import GnaniProvider
p = GnaniProvider()
t = p.synthesize("నమస్కారం", "te-IN")
print("TTS bytes:", len(t.audio), t.mime)
stt = p.transcribe(t.audio, "te-IN")
print("STT:", stt.text, stt.confidence)
```
