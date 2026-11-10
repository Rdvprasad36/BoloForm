# Social Media Posts

## LinkedIn Post Draft

Excited to share **Bolo Form** — my project for the #GreatIndianAIInternshipChallenge by #GnaniAI! 🇮🇳

Millions of citizens in India, especially rural farmers and older citizens, find standard English web forms intimidating and inaccessible. They often end up relying on third-party intermediaries who charge fees or make clerical errors on subsidy applications.

I built **Bolo Form** to solve this:
🗣️ **Voice-First in Telugu**: Users answer naturally in their spoken language using Gnani's **Timbre TTS** (voice: Shivani) and **Prisma STT** (v2.5).
🛡️ **Risk-Adaptive Confirmations**: Critical information (phone numbers, land area) is read back digit-by-digit so mishearings are caught immediately before committing.
🔌 **One-Tag Embed Widget**: Any company or government agency can add `<script src="/embed.js">` to their existing English form. The widget interviews the user in Telugu and fills the host company's English form inputs live via `postMessage`.
🔒 **Zero Audio Storage**: No user audio is ever stored on disk, and submissions expire automatically.

Measured Latency on live Gnani models:
- Timbre TTS (v3.0): median (p50) 2.2s
- Prisma STT (v2.5): median (p50) 1.6s
- 85 automated tests passing with 100% offline mock capability.

Check out the code and live demo here: https://github.com/Rdvprasad36/BoloForm

#GreatIndianAIInternshipChallenge #GnaniAI #VoiceAI #IndicAI #AIForBharat #FastAPI #Inclusion

---

## X (Twitter) Post Draft

English web forms shouldn't stop rural citizens from accessing government schemes.

For the #GreatIndianAIInternshipChallenge, I built **Bolo Form**:
1. Speak Telugu to an embeddable voice widget.
2. Verified with @GnaniAI Prisma STT & Timbre TTS.
3. Fills host forms live in English!

Check out the repo: https://github.com/Rdvprasad36/BoloForm
#GnaniAI #IndicAI
