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
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Any

import httpx

from ..extensions import db
from ..models import Booking, CaseFile, EmailLog, User
from .slots import format_wat

RESEND_API_URL = "https://api.resend.com/emails"
RESEND_TIMEOUT_S = 30.0
SEND_ATTEMPTS = 2  # initial try plus one retry

KIND_REQUEST_PROFESSOR = "session_request_professor"
KIND_REQUEST_STUDENT = "request_received_student"
KIND_CONFIRMED_PROFESSOR = "booking_confirmed_professor"
KIND_CONFIRMED_STUDENT = "booking_confirmed_student"
KIND_DECLINED_STUDENT = "booking_declined_student"
KIND_CANCELLED_PROFESSOR = "booking_cancelled_professor"
KIND_MESSAGE_BASE = "new_message"

MESSAGE_EMAIL_BATCH = timedelta(hours=1)

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


def case_file_context(case: CaseFile) -> dict[str, Any]:
    """Shared case-file data for the email and the professor page.

    Both surfaces render from this context so the page always shows the
    same content the professor received by email.
    """
    gaps = _top_gaps(case)
    diagnosis = case.diagnosis or {}
    return {
        "core_problem": str(diagnosis.get("core_problem", "—")),
        "gaps": [
            {
                "category": str(gap.get("category", "other")),
                "description": str(gap.get("description", "")),
                "severity": gap.get("severity", 1) or 1,
                "evidence": _short_quote(gap.get("evidence", []) or []),  # type: ignore[arg-type]
            }
            for gap in gaps
        ],
        "questions": [
            str(item)
            for item in diagnosis.get("questions_for_professor", []) or []
        ],
        "tried": [
            str(item)
            for item in diagnosis.get("what_student_already_tried", []) or []
        ],
        "agenda": _agenda(gaps),
    }


def build_case_file_email(
    *,
    booking: Booking,
    case: CaseFile,
    professor: User,
    student: User,
    review_url: str | None = None,
) -> OutgoingEmail:
    """Professor case file: diagnosis brief, evidence, questions, agenda.

    With ``review_url`` this is the session-request email: it links to the
    review page instead of the meeting link, which stays hidden until the
    professor accepts.
    """
    ctx = case_file_context(case)
    gaps = ctx["gaps"]
    questions = ctx["questions"]
    tried = ctx["tried"]
    agenda = ctx["agenda"]
    slot = format_wat(booking.scheduled_at) if booking.scheduled_at else "—"
    meeting = booking.meeting_url or "—"

    def gap_text(gap: dict[str, Any], index: int) -> str:
        return (
            f"{index}. [{gap['category']}] {gap['description']}\n"
            f"   Evidence: {gap['evidence']}"
        )

    text_lines = [
        f"Case file for {student.display_name} (Mentora Academic Hub).",
        "",
        "Core problem:",
        str(ctx["core_problem"]),
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
        "\n".join(f"- {item}" for item in agenda),
        "",
        f"Session: {slot} · 60 minutes",
        *(
            [f"Review request: {review_url}"]
            if review_url
            else [f"Meeting link: {meeting}"]
        ),
        "",
        "Sent from the Mentora Academic Hub demo.",
    ]
    if student.is_sample or professor.is_sample:
        text_lines.append("[SAMPLE DATA] Synthetic demo content; not a real person.")

    def gap_html(gap: dict[str, Any]) -> str:
        return (
            "<li><strong>["
            + html.escape(str(gap["category"]))
            + "]</strong> "
            + html.escape(str(gap["description"]))
            + "<br>Evidence: <em>"
            + html.escape(str(gap["evidence"]))
            + "</em></li>"
        )

    def list_html(items: list[object], empty: str) -> str:
        if not items:
            return f"<p>{empty}</p>"
        return (
            "<ul>" + "".join(f"<li>{html.escape(str(i))}</li>" for i in items) + "</ul>"
        )

    if review_url:
        target = html.escape(review_url)
        session_link_html = f'Review request: <a href="{target}">{target}</a>'
    else:
        target = html.escape(meeting)
        session_link_html = f'Meeting link: <a href="{target}">{target}</a>'

    html_body = f"""<div style="font-family:Arial,sans-serif;max-width:640px;color:#0B1B33">
<div style="background:#0E6B5C;color:#fff;padding:16px 20px;border-radius:12px 12px 0 0">
<strong>Mentora Academic Hub — case file for {html.escape(student.display_name)}</strong>
</div>
<div style="border:1px solid #E7E2D9;border-top:none;padding:20px;border-radius:0 0 12px 12px">
<h2 style="margin-top:0">Core problem</h2>
<p>{html.escape(str(ctx["core_problem"]))}</p>
<h2>Top gaps</h2>
{"<ol>" + "".join(gap_html(g) for g in gaps) + "</ol>" if gaps else "<p>None recorded.</p>"}
<h2>The student's questions</h2>
{list_html(questions, "None recorded.")}
<h2>What the student already tried</h2>
{list_html(tried, "None recorded.")}
<h2>Suggested 45-minute agenda</h2>
{list_html(agenda, "")}
<h2>Session</h2>
<p>{html.escape(slot)} · 60 minutes<br>
{session_link_html}</p>
<p style="color:#5B6475;font-size:13px">Sent from the Mentora Academic Hub demo.
{"[SAMPLE DATA] Synthetic demo content; not a real person." if student.is_sample or professor.is_sample else ""}</p>
</div></div>"""
    subject_kind = "session request" if review_url else "case file"
    return OutgoingEmail(
        to=professor.email,
        subject=f"Mentora {subject_kind}: {student.display_name} — {slot}",
        text="\n".join(text_lines),
        html_body=html_body,
    )


def build_confirmation_email(
    *, booking: Booking, professor: User, student: User
) -> OutgoingEmail:
    """Student receipt: who, when (WAT), meeting link, demo receipt ref.

    Sent only once the professor accepts, so the meeting link is final.
    """
    slot = format_wat(booking.scheduled_at) if booking.scheduled_at else "—"
    meeting = booking.meeting_url or "—"
    text = "\n".join(
        [
            f"Your session with {professor.display_name} is confirmed.",
            "",
            f"When: {slot} · 60 minutes",
            f"Meeting link: {meeting}",
            f"Receipt: {booking.mock_payment_ref or '—'} (demo, captured)",
            "",
            "Your diagnosis was shared with the professor for preparation.",
            "",
            "Sent from the Mentora Academic Hub demo.",
        ]
    )
    html_body = f"""<div style="font-family:Arial,sans-serif;max-width:640px;color:#0B1B33">
<div style="background:#0E6B5C;color:#fff;padding:16px 20px;border-radius:12px 12px 0 0">
<strong>Session confirmed</strong>
</div>
<div style="border:1px solid #E7E2D9;border-top:none;padding:20px;border-radius:0 0 12px 12px">
<p>Your session with <strong>{html.escape(professor.display_name)}</strong> is confirmed.</p>
<p>When: <strong>{html.escape(slot)}</strong> · 60 minutes<br>
Meeting link: <a href="{html.escape(meeting)}">{html.escape(meeting)}</a><br>
Receipt: {html.escape(booking.mock_payment_ref or "—")} (demo, captured)</p>
<p>Your diagnosis was shared with the professor for preparation.</p>
<p style="color:#5B6475;font-size:13px">Sent from the Mentora Academic Hub demo.</p>
</div></div>"""
    return OutgoingEmail(
        to=student.email,
        subject=f"Session confirmed: {professor.display_name} — {slot}",
        text=text,
        html_body=html_body,
    )


def build_request_received_email(
    *, booking: Booking, professor: User, student: User
) -> OutgoingEmail:
    """Student notice: the request is with the professor (no link yet)."""
    slot = format_wat(booking.scheduled_at) if booking.scheduled_at else "—"
    text = "\n".join(
        [
            f"Your session request is with {professor.display_name}.",
            "",
            f"When: {slot} · 60 minutes",
            "They have up to 48 hours to accept, decline or propose a time.",
            f"Receipt: {booking.mock_payment_ref or '—'} "
            "(demo payment held, not charged)",
            "",
            "Sent from the Mentora Academic Hub demo.",
        ]
    )
    html_body = f"""<div style="font-family:Arial,sans-serif;max-width:640px;color:#0B1B33">
<div style="background:#0E6B5C;color:#fff;padding:16px 20px;border-radius:12px 12px 0 0">
<strong>Request received</strong>
</div>
<div style="border:1px solid #E7E2D9;border-top:none;padding:20px;border-radius:0 0 12px 12px">
<p>Your session request is with <strong>{html.escape(professor.display_name)}</strong>.</p>
<p>When: <strong>{html.escape(slot)}</strong> · 60 minutes<br>
They have up to 48 hours to accept, decline or propose a time.<br>
Receipt: {html.escape(booking.mock_payment_ref or "—")} (demo payment held, not charged)</p>
<p style="color:#5B6475;font-size:13px">Sent from the Mentora Academic Hub demo.</p>
</div></div>"""
    return OutgoingEmail(
        to=student.email,
        subject=f"Request received: {professor.display_name} — {slot}",
        text=text,
        html_body=html_body,
    )


def build_confirmed_professor_email(
    *, booking: Booking, student: User
) -> OutgoingEmail:
    """Professor receipt: the session they accepted, with the meeting link."""
    slot = format_wat(booking.scheduled_at) if booking.scheduled_at else "—"
    meeting = booking.meeting_url or "—"
    text = "\n".join(
        [
            f"You accepted {student.display_name}'s session request.",
            "",
            f"When: {slot} · 60 minutes",
            f"Meeting link: {meeting}",
            "",
            "Sent from the Mentora Academic Hub demo.",
        ]
    )
    html_body = f"""<div style="font-family:Arial,sans-serif;max-width:640px;color:#0B1B33">
<div style="background:#0E6B5C;color:#fff;padding:16px 20px;border-radius:12px 12px 0 0">
<strong>Session confirmed</strong>
</div>
<div style="border:1px solid #E7E2D9;border-top:none;padding:20px;border-radius:0 0 12px 12px">
<p>You accepted <strong>{html.escape(student.display_name)}</strong>'s session request.</p>
<p>When: <strong>{html.escape(slot)}</strong> · 60 minutes<br>
Meeting link: <a href="{html.escape(meeting)}">{html.escape(meeting)}</a></p>
<p style="color:#5B6475;font-size:13px">Sent from the Mentora Academic Hub demo.</p>
</div></div>"""
    professor = db.session.get(User, booking.professor_id)
    return OutgoingEmail(
        to=professor.email if professor else "",
        subject=f"Session confirmed: {student.display_name} — {slot}",
        text=text,
        html_body=html_body,
    )


def build_declined_email(
    *, booking: Booking, professor: User, student: User
) -> OutgoingEmail:
    """Student notice: the request was declined, with the reason."""
    slot = format_wat(booking.scheduled_at) if booking.scheduled_at else "—"
    reason = booking.decline_reason or "No reason given."
    text = "\n".join(
        [
            f"{professor.display_name} declined your session request.",
            "",
            f"When: {slot} · 60 minutes",
            f"Reason: {reason}",
            "Your demo payment hold was released; pick another time or match.",
            "",
            "Sent from the Mentora Academic Hub demo.",
        ]
    )
    html_body = f"""<div style="font-family:Arial,sans-serif;max-width:640px;color:#0B1B33">
<div style="background:#0E6B5C;color:#fff;padding:16px 20px;border-radius:12px 12px 0 0">
<strong>Request declined</strong>
</div>
<div style="border:1px solid #E7E2D9;border-top:none;padding:20px;border-radius:0 0 12px 12px">
<p><strong>{html.escape(professor.display_name)}</strong> declined your session request.</p>
<p>When: <strong>{html.escape(slot)}</strong> · 60 minutes<br>
Reason: {html.escape(reason)}<br>
Your demo payment hold was released; pick another time or match.</p>
<p style="color:#5B6475;font-size:13px">Sent from the Mentora Academic Hub demo.</p>
</div></div>"""
    return OutgoingEmail(
        to=student.email,
        subject=f"Request declined: {professor.display_name} — {slot}",
        text=text,
        html_body=html_body,
    )


def _booking_parties(
    booking_id: int,
) -> tuple[Booking, CaseFile | None, User, User] | None:
    """Booking plus case/professor/student; None when anyone is missing."""
    booking = db.session.get(Booking, booking_id)
    if booking is None:
        return None
    case = (
        db.session.get(CaseFile, booking.case_id) if booking.case_id else None
    )
    professor = db.session.get(User, booking.professor_id)
    student = db.session.get(User, booking.student_id)
    if professor is None or student is None:
        return None
    return booking, case, professor, student


def send_request_emails(booking_id: int, *, review_url: str) -> list[EmailLog]:
    """Session-request email to the professor, receipt to the student.

    The case file goes out only with the student's consent flag. Every
    outcome lands in EmailLog; unexpected errors propagate to the caller,
    which must not let them break the booking.
    """
    parties = _booking_parties(booking_id)
    if parties is None:
        return []
    booking, case, professor, student = parties
    logs = []
    if booking.consent_share_diagnosis and case is not None:
        logs.append(
            send_logged_email(
                booking_id=booking.id,
                kind=KIND_REQUEST_PROFESSOR,
                email=build_case_file_email(
                    booking=booking,
                    case=case,
                    professor=professor,
                    student=student,
                    review_url=review_url,
                ),
            )
        )
    logs.append(
        send_logged_email(
            booking_id=booking.id,
            kind=KIND_REQUEST_STUDENT,
            email=build_request_received_email(
                booking=booking, professor=professor, student=student
            ),
        )
    )
    return logs


def send_accepted_emails(booking_id: int) -> list[EmailLog]:
    """Confirmed emails to both sides, each carrying the meeting link."""
    parties = _booking_parties(booking_id)
    if parties is None:
        return []
    booking, _case, professor, student = parties
    return [
        send_logged_email(
            booking_id=booking.id,
            kind=KIND_CONFIRMED_PROFESSOR,
            email=build_confirmed_professor_email(
                booking=booking, student=student
            ),
        ),
        send_logged_email(
            booking_id=booking.id,
            kind=KIND_CONFIRMED_STUDENT,
            email=build_confirmation_email(
                booking=booking, professor=professor, student=student
            ),
        ),
    ]


def send_declined_email(booking_id: int) -> EmailLog | None:
    """Decline notice to the student, carrying the professor's reason."""
    parties = _booking_parties(booking_id)
    if parties is None:
        return None
    booking, _case, professor, student = parties
    return send_logged_email(
        booking_id=booking.id,
        kind=KIND_DECLINED_STUDENT,
        email=build_declined_email(
            booking=booking, professor=professor, student=student
        ),
    )


def build_cancelled_email(
    *, booking: Booking, professor: User, student: User
) -> OutgoingEmail:
    """Professor notice: the student withdrew the request; slot freed."""
    slot = format_wat(booking.scheduled_at) if booking.scheduled_at else "—"
    text = "\n".join(
        [
            f"{student.display_name} cancelled the session request for {slot}.",
            "",
            "The slot is free again and the demo hold was released; no action needed.",
            "",
            "Sent from the Mentora Academic Hub demo.",
        ]
    )
    html_body = f"""<div style="font-family:Arial,sans-serif;max-width:640px;color:#0B1B33">
<div style="background:#0E6B5C;color:#fff;padding:16px 20px;border-radius:12px 12px 0 0">
<strong>Request cancelled</strong>
</div>
<div style="border:1px solid #E7E2D9;border-top:none;padding:20px;border-radius:0 0 12px 12px">
<p><strong>{html.escape(student.display_name)}</strong> cancelled the session request for <strong>{html.escape(slot)}</strong>.</p>
<p>The slot is free again and the demo hold was released; no action needed.</p>
<p style="color:#5B6475;font-size:13px">Sent from the Mentora Academic Hub demo.</p>
</div></div>"""
    return OutgoingEmail(
        to=professor.email,
        subject=f"Request cancelled: {student.display_name} — {slot}",
        text=text,
        html_body=html_body,
    )


def send_cancelled_email(booking_id: int) -> EmailLog | None:
    """Cancellation notice to the professor only (no student email)."""
    parties = _booking_parties(booking_id)
    if parties is None:
        return None
    booking, _case, professor, student = parties
    return send_logged_email(
        booking_id=booking.id,
        kind=KIND_CANCELLED_PROFESSOR,
        email=build_cancelled_email(
            booking=booking, professor=professor, student=student
        ),
    )


def build_new_message_email(
    *, recipient: User, sender: User, snippet: str, thread_url: str
) -> OutgoingEmail:
    """Thread ping with the message opening; links back to the thread."""
    text = "\n".join(
        [
            f"New message from {sender.display_name}:",
            "",
            snippet,
            "",
            f"Read and reply: {thread_url}",
            "",
            "Sent from the Mentora Academic Hub demo.",
        ]
    )
    html_body = f"""<div style="font-family:Arial,sans-serif;max-width:640px;color:#0B1B33">
<div style="background:#0E6B5C;color:#fff;padding:16px 20px;border-radius:12px 12px 0 0">
<strong>New message</strong>
</div>
<div style="border:1px solid #E7E2D9;border-top:none;padding:20px;border-radius:0 0 12px 12px">
<p>New message from <strong>{html.escape(sender.display_name)}</strong>:</p>
<blockquote style="border-left:4px solid #C9A227;padding:8px 12px;color:#5B6475">{html.escape(snippet)}</blockquote>
<p><a href="{html.escape(thread_url)}">Read and reply</a></p>
<p style="color:#5B6475;font-size:13px">Sent from the Mentora Academic Hub demo.</p>
</div></div>"""
    return OutgoingEmail(
        to=recipient.email,
        subject=f"New message from {sender.display_name}",
        text=text,
        html_body=html_body,
    )


def send_message_email(
    booking_id: int, sender_id: int, *, thread_url: str, snippet: str
) -> EmailLog | None:
    """Thread ping email, at most one per thread per hour.

    The kind carries the UTC hour bucket so the per-(booking, kind)
    idempotency still dedupes retries without blocking next hour's ping.
    Returns None when a ping went out within the past hour.
    """
    parties = _booking_parties(booking_id)
    if parties is None:
        return None
    booking, _case, professor, student = parties
    recipient = student if sender_id == professor.id else professor
    if sender_id not in (student.id, professor.id):
        return None
    now = datetime.now(timezone.utc)
    recent = (
        EmailLog.query.filter(
            EmailLog.booking_id == booking.id,
            EmailLog.kind.startswith(KIND_MESSAGE_BASE),
            EmailLog.status == STATUS_SENT,
            EmailLog.created_at
            > (now - MESSAGE_EMAIL_BATCH).replace(tzinfo=None),
        ).first()
    )
    if recent is not None:
        return None
    sender = student if sender_id == student.id else professor
    return send_logged_email(
        booking_id=booking.id,
        kind=f"{KIND_MESSAGE_BASE}:{now.strftime('%Y%m%dT%H')}",
        email=build_new_message_email(
            recipient=recipient, sender=sender, snippet=snippet[:200],
            thread_url=thread_url,
        ),
    )
