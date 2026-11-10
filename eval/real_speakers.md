# Real Speakers Evaluation Protocol (Small Sample)

## Purpose
Evaluate Gnani Prisma STT (v2.5) on real human Telugu speakers (not synthetic TTS speech), across clean/quiet and noisy takes, using synthetic/fake persona data.

## Protocol
1. **Consent & Privacy**:
   - 3 consenting speakers (Speaker A, Speaker B, Speaker C).
   - No real personal data (PII) spoken — speakers read synthetic test persona prompts.
   - Recordings are discarded immediately after transcription; transcripts contain only fake demo data.

2. **Test Personas**:
   - Persona 1: "నా పేరు రాము", 35, "గొల్లపాలెం", "విశాఖపట్నం", "9876543210", "రెండున్నర ఎకరాలు", "వరి", "అవును"
   - Persona 2: "లక్ష్మి", 42, "కొత్తవలస", "విజయనగరం", "8765432109", "ఐదు ఎకరాలు", "మిరప", "కాదు"
   - Persona 3: "సత్యనారాయణ", 58, "తాటిపర్తి", "కాకినాడ", "7654321098", "మూడున్నర ఎకరాలు", "పత్తి", "అవును"

3. **Conditions**:
   - **Quiet**: Normal indoor room with low background noise.
   - **Noisy**: Background domestic sounds / ambient noise (~15 dB SNR).

4. **Scoring Script**:
   Run `python -m eval.score_speakers` to compare transcripts against ground truth and report field-level accuracy and error patterns.
