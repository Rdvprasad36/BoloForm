# Final Submission Checklist — Bolo Form

Deadline: **Nov 10, 2026, 11:59 PM IST** (Submit at least 1 hour early!)

### Repository & Code
- [x] Code is clean, documented, and fully pushed to `https://github.com/Rdvprasad36/BoloForm.git`.
- [x] Repository visibility is confirmed **Public**.
- [x] All 85 unit and integration tests pass with `python -m pytest -v`.
- [x] Offline mode works completely with `PROVIDER=mock` (zero network/API key required).

### Security & Privacy
- [x] **No API keys or secrets in Git history**. (`git log -p` verified, `.env` gitignored).
- [x] No user audio recorded or saved to disk.
- [x] No real personal PII used in demo, tests, or eval (strictly synthetic data).
- [x] Submissions auto-expire (`SUBMISSION_TTL_HOURS`) and `/api/submissions/{id}` delete endpoint verified.
- [x] CSV formula injection protection implemented and tested.

### Deployment & Live Demo
- [ ] Deployed to Render via `Dockerfile` and `DEPLOY.md`.
- [ ] Tested on a real mobile browser over HTTPS (`https://...onrender.com/demo/company.html`).
- [ ] Verified microphone access works over HTTPS.
- [ ] Verified Telugu voice entry populates the host English form live.

### Challenge Submission Requirements
- [x] `submission/explanation.md` completed with real measured latencies and architecture diagram.
- [x] `submission/demo_script_60s.md` shot list prepared for 60-second video recording.
- [x] `submission/social_posts.md` drafts ready for LinkedIn and X with official hashtags `#GreatIndianAIInternshipChallenge` and `#GnaniAI`.
- [x] Submit nomination link and repository URL on the challenge submission portal at least 60 minutes before 11:59 PM IST.
