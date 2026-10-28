# DECISIONS.md — one line per architectural decision.

- 2026-10-28: Meta calls go through the OpenAI Python SDK pointed at the Meta base URL (Meta publishes no dedicated client; this is the docs' recommended path).
- 2026-10-28: Chat Completions protocol first for lower scaffold complexity; switch to Responses API later if multi-turn reasoning continuity proves necessary.
- 2026-10-28: Model IDs come only from env vars (META_MODEL_AGENT/FAST/TRANSCRIBE) with no code defaults, so credit spend stays configurable.
- 2026-10-28: META_BASE_URL defaults to the documented https://api.meta.ai/v1 but is env-overridable; META_API_KEY has no default and fails fast.
- 2026-10-28: Tool loop depends on a ChatClient protocol (SDK adapter in prod, fakes in tests) so agent logic is unit-testable with no network.
- 2026-10-28: Retries use our own exponential backoff (rate limits, transport/timeout errors, 5xx) with the SDK's built-in retries disabled to avoid stacked retry storms.
- 2026-10-28: Tables are created with db.create_all and no migrations until the schema stabilizes after the auth step.
- 2026-10-28: Roles/statuses/levels are plain strings without DB CHECK constraints; validation moves into forms/services when those steps land.
- 2026-10-28: User carries email (unique), password_hash (nullable until auth), display_name, role, is_sample flag and timestamps.
- 2026-10-28: Foreign keys are wired now (profiles→user, documents/casefiles/bookings→users, sessions→bookings, notes→student/session).
- 2026-10-28: Datetimes are stored naive UTC (SQLite has no tz-aware type); revisit with timezone-aware columns if we leave SQLite.
- 2026-10-28: ProfessorProfile.rate is a unit-less float; currency is decided at the booking step, not guessed now.
- 2026-10-28: Seed data is synthetic, @example.com emails, is_sample=True, "[SAMPLE DATA]" bios; seed is idempotent get-or-create by email.
- 2026-10-28: Email (Resend vs SMTP) and PDF (reportlab vs WeasyPrint) providers stay undecided; services are typed NotImplementedError stubs.
- 2026-10-28: Verified on the machine's Python 3.14 while keeping the code 3.11-compatible; no 3.11 interpreter is installed here.
