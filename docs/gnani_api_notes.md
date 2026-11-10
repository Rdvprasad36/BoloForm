# Gnani API notes
Source: docs.gnani.ai (copy the exact text; add the date). Everything in `app/providers/gnani.py` is
configured from `.env` using what you write here. Do not guess any value.

Copied on: ____

## Auth
- Header name and format (e.g. `Authorization: Bearer <key>`): ____
- Where the key is created: ____
- .env: `GNANI_API_KEY=...`, `GNANI_STT_AUTH=Header-Name: value {key}`, `GNANI_TTS_AUTH=...`

## Prisma (STT)
- Endpoint URL -> `GNANI_STT_URL`: ____
- Request style: multipart file upload or JSON with base64 audio? -> `GNANI_STT_MODE`: ____
- Name of the file field (multipart) -> `GNANI_STT_FILE_FIELD`: ____
- Extra fields such as language -> `GNANI_STT_FIELDS` (JSON, may use `{lang}`): ____
- Telugu supported? language code -> `GNANI_LANG_CODE`: ____
- Audio format / sample rate / max duration (the app sends 16 kHz mono 16-bit WAV): ____
- Request example (paste exactly):

```
____
```
- Response example (paste exactly):

```
____
```
- Path to the transcript in the response -> `GNANI_STT_TEXT_PATH` (dotted, e.g. `data.text`): ____
- Confidence returned? path -> `GNANI_STT_CONF_PATH`: ____
- Streaming available? (not used by this build): ____
- Credit cost per call or minute: ____

## Timbre (TTS)
- Endpoint URL -> `GNANI_TTS_URL`: ____
- JSON body shape -> `GNANI_TTS_BODY` (use `{text}`, `{lang}`, `{voice}`): ____
- Telugu voices available -> `GNANI_TTS_VOICE`: ____
- Response: raw audio bytes or JSON with base64? -> `GNANI_TTS_RESPONSE`, `GNANI_TTS_AUDIO_PATH`: ____
- Output format (WAV/MP3) and sample rate -> `GNANI_TTS_MIME`: ____
  - The app plays any browser-supported format. The EVAL harness needs WAV; if Timbre returns MP3, convert to WAV first.
- Request example / Response example:

```
____
```
- Credit cost: ____

## Limits and surprises
- Rate limits: ____
- Anything unexpected: ____

## Smoke test (do this before anything else)
```
PROVIDER=gnani python - <<'PY'
from app.providers.gnani import GnaniProvider
p = GnaniProvider()
t = p.synthesize("నమస్కారం", "te"); print("TTS bytes:", len(t.audio), t.mime)
open("/tmp/hello.wav", "wb").write(t.audio)
# If Timbre returns WAV, feed it back to Prisma:
print("STT:", p.transcribe(t.audio, "te").text)
PY
```
