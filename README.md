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
fail-fast, CSRF, hardened cookies) and a live Meta API check script, Step 3a
student intake with document diagnosis and a live agent timeline, Step 3b
parallel specialists, evidence-based professor matching and live eval scripts,
Step 4 booking (slot grid, consent, demo checkout, sessions pages) and email
(Resend HTTPS or local outbox, case-file + confirmation emails).
No recording, transcription or PDF notes code exists yet.

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
and role guards, tokenless POSTs rejected with CSRF on. Intake coverage:
PDF/DOCX/TXT extraction, upload validation, grounding checker, owner-only
access, CSRF on the intake form, background pipeline runs (fake client).
Parallel coverage: specialist merge/rank, partial and total failure, merge
failure, bad mode flag. Matching coverage: tool scoring, ranking validator,
retry-once, budget degrade, tool-call logging, professors routes. Booking
coverage: slot grid and timezones, double-booking race, consent gating,
sessions access. Email coverage: providers, recipient override, idempotency,
refusals, content builders.

## Layout

```text
app/
  __init__.py        app factory, blueprint registration
  config.py          env-only config (see .env.example)
  extensions.py      shared extensions (db)
  models.py          User, ProfessorProfile, StudentProfile, Document,
                     CaseFile, Booking, SessionRecord, MemoryNote, RunEvent,
                     MatchResult, EmailLog, ToolCallLog
  security.py        current_user, login_required, role_required
  blueprints/        auth (register/login/logout), cases (dashboard, intake,
                     detail, events, booking, sessions),
                     professors (public directory), bookings, agent (health)
  templates/         base shell + design macros (_ui.html) + auth/case pages
  services/
    meta_client.py   Meta API: retries, structured output, run_tool_loop
    extraction.py    upload validation, storage, text extraction
    diagnosis.py     parallel/single diagnosis, grounding, intake pipeline
    matching.py      professor tools, ranking, validation, match runner
    slots.py         60-minute slot grid (UTC store, WAT display)
    booking.py       race-safe booking creation, Jitsi links, demo refs
    email_service.py Resend HTTPS or local outbox, case-file + confirmation
    transcription.py stub (Muse Voice Transcribe)
    pdf_service.py   stub (library TBD)
scripts/seed.py      idempotent synthetic seed (20 profs / 4 depts / 3 students)
scripts/check_meta.py live Meta API smoke test (never run by pytest)
scripts/make_samples.py regenerates samples/ fixtures
scripts/make_matching_cases.py regenerates eval/matching_cases.json
scripts/eval_diagnosis.py live diagnosis eval (never run by pytest)
scripts/eval_matching.py live matching eval (never run by pytest)
samples/             synthetic thesis excerpts + expected.json (demo fixtures)
eval/                30 generated matching-eval cases
docs/eval/           eval reports (written by the eval scripts)
tests/               pytest suite (smoke, auth, intake, parallel, matching,
                     booking, email)
```

## Live API check

`python -m scripts.check_meta [--audio file.wav]` makes one minimal real call
per check: agent tool round trip, fast-model structured JSON, native PDF vs
extracted text on the agent model, and optional WAV transcription with speaker
labels. It prints model, latency and token usage per call, never prints
secrets, and exits non-zero with the exact error on any failure. Requires
`META_API_KEY` plus the `META_MODEL_*` ids in `.env`; each run spends a small
amount of API credit.

## Intake demo

Log in as a seeded student (any `sample-student-0X@example.com` address with
`SEED_DEMO_PASSWORD`), open Dashboard, and submit a new request with
`samples/thesis_excerpt_stats.pdf` attached. The case page shows the agent
timeline on the right as each real step completes, then the diagnosis with
grounded evidence quotes plus three recommended professors on the left.

## Booking + email demo

From a finished case, open "Book session" on any match card: pick a WAT slot,
tick the diagnosis-sharing consent, and confirm through the clearly labeled
demo checkout (nothing is charged or stored). The session lands under Sessions
with a Jitsi link. Emails default to the local `outbox/` provider (gitignored
`.eml` files, never delivered). For real delivery set `EMAIL_PROVIDER=resend`,
`RESEND_API_KEY`, and `DEMO_RECIPIENT_OVERRIDE` to your own inbox: the Resend
sandbox only delivers to the account owner, `@example.com` sample addresses
are refused outright, and every redirected email carries a
"Demo: intended for" banner. Each booking sends each email kind at most once
(`EmailLog`); mail failures never break the booking.

## Evaluation

Live scripts (real Meta calls, real credit; never run by pytest):

```powershell
python -m scripts.eval_diagnosis [--mode both|parallel|single] [--reps 3]
python -m scripts.eval_matching [--limit N]
python -m scripts.make_matching_cases   # regenerate eval/matching_cases.json
```

`eval_diagnosis` compares found gaps with `samples/expected.json` over
repeated runs (planted-flaw recall, grounding rate, latency, tokens) and
writes `docs/eval/diagnosis.md`. `eval_matching` runs the 30 generated cases
(top-1/top-3 accuracy, latency, tokens) and writes `docs/eval/matching.md`.
Both need `META_API_KEY` plus the `META_MODEL_*` ids in `.env`;
`eval_matching` also needs `SEED_DEMO_PASSWORD`. Start matching with
`--limit 3`: a full run is 30 Wonder calls.

## Design credits

Headings are set in Fraunces and UI text in Inter (Google Fonts, SIL OFL).
All icons are original inline SVGs drawn for this project in the Lucide/Feather
stroke style (ISC-licensed references); the logo mark is original artwork.

## License

MIT — see [LICENSE](LICENSE).
