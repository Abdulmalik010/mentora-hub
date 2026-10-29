# Mentora Academic Hub

Students find professors, lecturers and experts for thesis, coursework and
project help. An agent (not a chatbot) diagnoses the student's gap from their
documents, matches professors via tools, books sessions, briefs the professor,
and turns recorded sessions into reviewed notes PDFs.

## Built during the hackathon

Built for the Meta Global AI Developer Hackathon 2026 (indie developer track,
"Build for Your World" problem statement), Oct 27 – Nov 4, 2026. Everything in
this repo was created during the event: scaffold, data, auth, agent, booking,
transcription, evaluation and demo. All AI calls go through Meta models via the
[Meta Model API](https://dev.meta.ai/docs). All professors and students in the
seed data are synthetic sample data — no real names or photos.

Built so far: Step 1 scaffold (factory, models, seed, Meta client, smoke
tests), Step 2 session auth (register/login/logout, role guards) plus the base
Jinja + Tailwind shell, Step 2b security close-out (seed demo logins, SECRET_KEY
fail-fast, CSRF, hardened cookies) and a live Meta API check script. No agent,
matching, booking, email, transcription, PDF or eval code exists yet.

## Stack

Python 3.11, Flask (app factory), SQLite via SQLAlchemy (`db.create_all`, no
migrations yet), Jinja + Tailwind CDN + vanilla JS (UI lands after the agent).
Tests: pytest.

## Quickstart (PowerShell)

```powershell
cd mentora
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env   # fill in SECRET_KEY, SEED_DEMO_PASSWORD, META_API_KEY + META_MODEL_*
python -m scripts.seed         # sample logins share SEED_DEMO_PASSWORD (sample-only)
flask --app app run
```

POSIX equivalent: `python3 -m venv .venv && source .venv/bin/activate`, rest as
above with `/` paths.

## Testing

```powershell
pytest -q
```

Smoke coverage: app factory boots, all 10 models import, seed yields 12
professors / 3 students, re-seed is idempotent, tool loop works with a fake
client (no network) and logs to `ToolCallLog`. Auth coverage:
register→login→logout, wrong-password/unknown-email rejection, duplicate and
invalid input rejection, seeded users log in, NULL-hash rows blocked, login
and role guards, tokenless POSTs rejected with CSRF on.

## Layout

```text
app/
  __init__.py        app factory, blueprint registration
  config.py          env-only config (see .env.example)
  extensions.py      shared extensions (db)
  models.py          User, ProfessorProfile, StudentProfile, Document,
                     CaseFile, Booking, SessionRecord, MemoryNote, ToolCallLog
  security.py        current_user, login_required, role_required
  blueprints/        auth (register/login/logout), professors, bookings,
                     agent (health routes only)
  templates/         base shell + index + auth pages (Jinja + Tailwind CDN)
  services/
    meta_client.py   Meta API: retries, structured output, run_tool_loop
    email_service.py stub (provider TBD)
    transcription.py stub (Muse Voice Transcribe)
    pdf_service.py   stub (library TBD)
scripts/seed.py      idempotent synthetic seed (12 profs / 4 depts / 3 students)
scripts/check_meta.py live Meta API smoke test (never run by pytest)
tests/               pytest suite (smoke + auth)
```

## Live API check

`python -m scripts.check_meta [--audio file.wav]` makes one minimal real call
per check: agent tool round trip, fast-model structured JSON, native PDF vs
extracted text on the agent model, and optional WAV transcription with speaker
labels. It prints model, latency and token usage per call, never prints
secrets, and exits non-zero with the exact error on any failure. Requires
`META_API_KEY` plus the `META_MODEL_*` ids in `.env`; each run spends a small
amount of API credit.

## License

MIT — see [LICENSE](LICENSE).
