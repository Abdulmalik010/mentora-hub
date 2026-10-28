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
Copy-Item .env.example .env   # then fill in META_API_KEY + META_MODEL_*
python -m scripts.seed
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
client (no network) and logs to `ToolCallLog`.

## Layout

```text
app/
  __init__.py        app factory, blueprint registration
  config.py          env-only config (see .env.example)
  extensions.py      shared extensions (db)
  models.py          User, ProfessorProfile, StudentProfile, Document,
                     CaseFile, Booking, SessionRecord, MemoryNote, ToolCallLog
  blueprints/        auth, professors, bookings, agent (health routes only)
  services/
    meta_client.py   Meta API: retries, structured output, run_tool_loop
    email_service.py stub (provider TBD)
    transcription.py stub (Muse Voice Transcribe)
    pdf_service.py   stub (library TBD)
scripts/seed.py      idempotent synthetic seed (12 profs / 4 depts / 3 students)
tests/test_smoke.py  pytest smoke suite
```

## License

MIT — see [LICENSE](LICENSE).
