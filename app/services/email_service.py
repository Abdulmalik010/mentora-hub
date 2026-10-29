"""Outbound email: Resend over HTTPS, or a local .eml outbox (the default).

Providers are selected by ``EMAIL_PROVIDER`` (``resend`` or ``outbox``).
``DEMO_RECIPIENT_OVERRIDE`` redirects every email to one inbox with a
"Demo: intended for <address>" banner. The Resend provider refuses
``@example.com`` recipients outright; the outbox writes local files only and
never delivers. Every send is logged to :class:`EmailLog`, idempotent per
(booking, kind), with one retry on transport/5xx failures.
"""
from __future__ import annotations

import html
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage

import httpx

from ..extensions import db
from ..models import Booking, CaseFile, EmailLog, User
from .slots import format_wat

RESEND_API_URL = "https://api.resend.com/emails"
RESEND_TIMEOUT_S = 30.0
SEND_ATTEMPTS = 2  # initial try plus one retry

KIND_CASE_FILE = "case_file_professor"
KIND_CONFIRMATION = "booking_confirmation_student"

DEFAULT_FROM = "onboarding@resend.dev"
STATUS_SENT = "sent"
STATUS_FAILED = "failed"
STATUS_REFUSED = "refused"


class EmailError(Exception):
    """A send attempt failed (provider error, transport error, bad config)."""


class EmailRefused(EmailError):
    """The email was refused before any provider call (guard rail)."""


@dataclass(frozen=True)
class OutgoingEmail:
    """One rendered email, before override handling."""

    to: str
    subject: str
    text: str
    html_body: str


@dataclass(frozen=True)
class EmailConfig:
    """Resolved email settings; read from env at each call for testability."""

    provider: str
    resend_api_key: str
    from_address: str
    override: str
    outbox_dir: str


def email_config() -> EmailConfig:
    """Read the email settings; outbox is the safe default provider."""
    return EmailConfig(
        provider=os.environ.get("EMAIL_PROVIDER", "outbox").strip().lower(),
        resend_api_key=os.environ.get("RESEND_API_KEY", "").strip(),
        from_address=os.environ.get("EMAIL_FROM", DEFAULT_FROM).strip(),
        override=os.environ.get("DEMO_RECIPIENT_OVERRIDE", "").strip(),
        outbox_dir=os.environ.get("EMAIL_OUTBOX_DIR", "outbox").strip()
        or "outbox",
    )


def apply_override(email: OutgoingEmail, override: str) -> OutgoingEmail:
    """Redirect to the demo inbox, bannered with the original recipient."""
    if not override or override == email.to:
        return email
    banner = f"Demo: intended for {email.to}"
    return OutgoingEmail(
        to=override,
        subject=f"[Demo] {email.subject}",
        text=f"{banner}\n\n{email.text}",
        html_body=(
            f'<p style="background:#FEF3C7;border:1px solid #C9A227;'
            f"padding:8px 12px;border-radius:8px;\">{html.escape(banner)}</p>"
            f"{email.html_body}"
        ),
    )


def _send_resend(
    email: OutgoingEmail, *, api_key: str, from_address: str
) -> str:
    """POST to Resend; return the provider id. 4xx fails fast, else one retry."""
    if not api_key:
        raise EmailError("RESEND_API_KEY is required for the resend provider")
    if email.to.lower().endswith("@example.com"):
        raise EmailRefused(
            f"refusing to send to sample address {email.to} "
            "(set DEMO_RECIPIENT_OVERRIDE for demos)"
        )
    payload = {
        "from": from_address,
        "to": [email.to],
        "subject": email.subject,
        "html": email.html_body,
        "text": email.text,
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    last_error = "unknown error"
    for _ in range(SEND_ATTEMPTS):
        try:
            response = httpx.post(
                RESEND_API_URL,
                json=payload,
                headers=headers,
                timeout=RESEND_TIMEOUT_S,
            )
        except httpx.HTTPError as exc:
            last_error = f"resend transport error: {exc}"
            continue
        if 200 <= response.status_code < 300:
            data = response.json()
            message_id = data.get("id", "")
            if not message_id:
                raise EmailError("resend accepted but returned no id")
            return str(message_id)
        snippet = response.text[:200].replace("\n", " ")
        last_error = f"resend error {response.status_code}: {snippet}"
        if 400 <= response.status_code < 500:
            break  # client errors will not heal on retry
    raise EmailError(f"{last_error} (after one retry)")


def _send_outbox(
    email: OutgoingEmail, *, from_address: str, outbox_dir: str
) -> str:
    """Write one .eml file; return its filename. Never delivers anything."""
    os.makedirs(outbox_dir, exist_ok=True)
    message = EmailMessage()
    message["From"] = from_address
    message["To"] = email.to
    message["Subject"] = email.subject
    message["Date"] = datetime.now(timezone.utc).strftime(
        "%a, %d %b %Y %H:%M:%S +0000"
    )
    message.set_content(email.text)
    message.add_alternative(email.html_body, subtype="html")
    filename = f"{uuid.uuid4().hex[:8]}.eml"
    with open(os.path.join(outbox_dir, filename), "wb") as handle:
        handle.write(message.as_bytes())
    return filename


def send_logged_email(
    *, booking_id: int, kind: str, email: OutgoingEmail
) -> EmailLog:
    """Send once per (booking, kind); failures become rows, never exceptions.

    Returns the existing sent row when this kind already went out. Unknown
    providers and refused addresses are logged, not raised.
    """
    existing = EmailLog.query.filter_by(
        booking_id=booking_id, kind=kind, status=STATUS_SENT
    ).first()
    if existing is not None:
        return existing
    config = email_config()
    final = apply_override(email, config.override)
    status = STATUS_SENT
    provider_id: str | None = None
    error: str | None = None
    try:
        if config.provider == "resend":
            provider_id = _send_resend(
                final,
                api_key=config.resend_api_key,
                from_address=config.from_address,
            )
        elif config.provider == "outbox":
            provider_id = _send_outbox(
                final,
                from_address=config.from_address,
                outbox_dir=config.outbox_dir,
            )
        else:
            raise EmailRefused(f"unknown EMAIL_PROVIDER: {config.provider}")
    except EmailRefused as exc:
        status = STATUS_REFUSED
        error = str(exc)[:500]
    except EmailError as exc:
        status = STATUS_FAILED
        error = str(exc)[:500]
    log = EmailLog(
        booking_id=booking_id,
        kind=kind,
        recipient=email.to,
        status=status,
        provider=config.provider,
        provider_id=provider_id,
        error=error,
    )
    db.session.add(log)
    db.session.commit()
    return log


def _top_gaps(case: CaseFile, limit: int = 3) -> list[dict[str, object]]:
    """Highest-severity gaps first (stable for ties)."""
    gaps = list((case.diagnosis or {}).get("gaps", []) or [])
    gaps.sort(key=lambda gap: -(gap.get("severity", 1) or 1))
    return gaps[:limit]  # type: ignore[return-value]


def _short_quote(evidence: list[dict[str, object]]) -> str:
    """First evidence quote trimmed for email (``"…" (p. N)``)."""
    if not evidence:
        return "(no quoted evidence)"
    quote = str(evidence[0].get("quote", "")).strip().replace("\n", " ")
    if len(quote) > 160:
        quote = quote[:157].rstrip() + "…"
    return f'"{quote}" (p. {evidence[0].get("page", "?")})'


def _agenda(gaps: list[dict[str, object]]) -> list[str]:
    """Static 45-minute agenda template filled with the actual top gaps."""
    first = str(gaps[0].get("description", "the main gap")) if gaps else "the main gap"
    second = (
        str(gaps[1].get("description", "the next gap"))
        if len(gaps) > 1
        else "follow-up questions"
    )
    return [
        f"0–10 min: goals and background — {first[:90]}",
        f"10–25 min: deep dive — {first[:90]}",
        f"25–35 min: deep dive — {second[:90]}",
        "35–45 min: action items and next steps",
    ]


def build_case_file_email(
    *, booking: Booking, case: CaseFile, professor: User, student: User
) -> OutgoingEmail:
    """Professor case file: diagnosis brief, evidence, questions, agenda."""
    diagnosis = case.diagnosis or {}
    gaps = _top_gaps(case)
    questions = diagnosis.get("questions_for_professor", []) or []
    tried = diagnosis.get("what_student_already_tried", []) or []
    slot = format_wat(booking.scheduled_at) if booking.scheduled_at else "—"
    meeting = booking.meeting_url or "—"

    def gap_text(gap: dict[str, object], index: int) -> str:
        return (
            f"{index}. [{gap.get('category', 'other')}] "
            f"{gap.get('description', '')}\n"
            f"   Evidence: {_short_quote(gap.get('evidence', []) or [])}"  # type: ignore[arg-type]
        )

    text_lines = [
        f"Case file for {student.display_name} (Mentora Academic Hub).",
        "",
        "Core problem:",
        str(diagnosis.get("core_problem", "—")),
        "",
        "Top gaps:",
        (
            "\n".join(gap_text(gap, i) for i, gap in enumerate(gaps, 1))
            if gaps
            else "None recorded."
        ),
        "",
        "The student's questions:",
        (
            "\n".join(f"- {item}" for item in questions)
            if questions
            else "None recorded."
        ),
        "",
        "What the student already tried:",
        "\n".join(f"- {item}" for item in tried) if tried else "None recorded.",
        "",
        "Suggested 45-minute agenda:",
        "\n".join(f"- {item}" for item in _agenda(gaps)),
        "",
        f"Session: {slot} · 60 minutes",
        f"Meeting link: {meeting}",
        "",
        "Sent from the Mentora Academic Hub demo.",
    ]
    if student.is_sample or professor.is_sample:
        text_lines.append("[SAMPLE DATA] Synthetic demo content; not a real person.")

    def gap_html(gap: dict[str, object]) -> str:
        return (
            "<li><strong>["
            + html.escape(str(gap.get("category", "other")))
            + "]</strong> "
            + html.escape(str(gap.get("description", "")))
            + "<br>Evidence: <em>"
            + html.escape(_short_quote(gap.get("evidence", []) or []))  # type: ignore[arg-type]
            + "</em></li>"
        )

    def list_html(items: list[object], empty: str) -> str:
        if not items:
            return f"<p>{empty}</p>"
        return (
            "<ul>" + "".join(f"<li>{html.escape(str(i))}</li>" for i in items) + "</ul>"
        )

    html_body = f"""<div style="font-family:Arial,sans-serif;max-width:640px;color:#0B1B33">
<div style="background:#0E6B5C;color:#fff;padding:16px 20px;border-radius:12px 12px 0 0">
<strong>Mentora Academic Hub — case file for {html.escape(student.display_name)}</strong>
</div>
<div style="border:1px solid #E7E2D9;border-top:none;padding:20px;border-radius:0 0 12px 12px">
<h2 style="margin-top:0">Core problem</h2>
<p>{html.escape(str(diagnosis.get("core_problem", "—")))}</p>
<h2>Top gaps</h2>
{"<ol>" + "".join(gap_html(g) for g in gaps) + "</ol>" if gaps else "<p>None recorded.</p>"}
<h2>The student's questions</h2>
{list_html(questions, "None recorded.")}
<h2>What the student already tried</h2>
{list_html(tried, "None recorded.")}
<h2>Suggested 45-minute agenda</h2>
{list_html(_agenda(gaps), "")}
<h2>Session</h2>
<p>{html.escape(slot)} · 60 minutes<br>
Meeting link: <a href="{html.escape(meeting)}">{html.escape(meeting)}</a></p>
<p style="color:#5B6475;font-size:13px">Sent from the Mentora Academic Hub demo.
{"[SAMPLE DATA] Synthetic demo content; not a real person." if student.is_sample or professor.is_sample else ""}</p>
</div></div>"""
    return OutgoingEmail(
        to=professor.email,
        subject=f"Mentora case file: {student.display_name} — {slot}",
        text="\n".join(text_lines),
        html_body=html_body,
    )


def build_confirmation_email(
    *, booking: Booking, professor: User, student: User
) -> OutgoingEmail:
    """Student receipt: who, when (WAT), meeting link, demo receipt ref."""
    slot = format_wat(booking.scheduled_at) if booking.scheduled_at else "—"
    meeting = booking.meeting_url or "—"
    text = "\n".join(
        [
            f"Your session with {professor.display_name} is booked.",
            "",
            f"When: {slot} · 60 minutes",
            f"Meeting link: {meeting}",
            f"Receipt: {booking.mock_payment_ref or '—'} (demo, nothing charged)",
            "",
            "Your diagnosis was shared with the professor for preparation.",
            "",
            "Sent from the Mentora Academic Hub demo.",
        ]
    )
    html_body = f"""<div style="font-family:Arial,sans-serif;max-width:640px;color:#0B1B33">
<div style="background:#0E6B5C;color:#fff;padding:16px 20px;border-radius:12px 12px 0 0">
<strong>Session booked</strong>
</div>
<div style="border:1px solid #E7E2D9;border-top:none;padding:20px;border-radius:0 0 12px 12px">
<p>Your session with <strong>{html.escape(professor.display_name)}</strong> is booked.</p>
<p>When: <strong>{html.escape(slot)}</strong> · 60 minutes<br>
Meeting link: <a href="{html.escape(meeting)}">{html.escape(meeting)}</a><br>
Receipt: {html.escape(booking.mock_payment_ref or "—")} (demo, nothing charged)</p>
<p>Your diagnosis was shared with the professor for preparation.</p>
<p style="color:#5B6475;font-size:13px">Sent from the Mentora Academic Hub demo.</p>
</div></div>"""
    return OutgoingEmail(
        to=student.email,
        subject=f"Session booked: {professor.display_name} — {slot}",
        text=text,
        html_body=html_body,
    )


def send_booking_emails(booking_id: int) -> list[EmailLog]:
    """Case-file email plus student confirmation; never raises.

    The case file goes out only with the student's consent flag. Every
    outcome lands in EmailLog; unexpected errors propagate to the caller,
    which must not let them break the booking.
    """
    booking = db.session.get(Booking, booking_id)
    if booking is None:
        return []
    case = (
        db.session.get(CaseFile, booking.case_id) if booking.case_id else None
    )
    professor = db.session.get(User, booking.professor_id)
    student = db.session.get(User, booking.student_id)
    if case is None or professor is None or student is None:
        return []
    logs = []
    if booking.consent_share_diagnosis:
        logs.append(
            send_logged_email(
                booking_id=booking.id,
                kind=KIND_CASE_FILE,
                email=build_case_file_email(
                    booking=booking,
                    case=case,
                    professor=professor,
                    student=student,
                ),
            )
        )
    logs.append(
        send_logged_email(
            booking_id=booking.id,
            kind=KIND_CONFIRMATION,
            email=build_confirmation_email(
                booking=booking, professor=professor, student=student
            ),
        )
    )
    return logs
