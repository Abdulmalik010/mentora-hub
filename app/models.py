"""SQLAlchemy models for Mentora Academic Hub (scaffold v1).

Tables are created with ``db.create_all()``; no migrations until the schema
stabilizes after the auth step. Roles, statuses and levels are plain strings
(see DECISIONS.md); datetimes are naive UTC (SQLite limitation).
"""
from __future__ import annotations

from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def _utcnow() -> datetime:
    """Naive UTC timestamp for SQLite ``DateTime`` columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(db.Model):
    """Login account; ``role`` is ``student`` or ``professor``."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=True)  # enforced at auth step
    display_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    is_sample = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    professor_profile = db.relationship(
        "ProfessorProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    student_profile = db.relationship(
        "StudentProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def set_password(self, password: str) -> None:
        """Hash and store a password; the app layer always sets this."""
        if not password:
            raise ValueError("password must not be empty")
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """True on match; False on mismatch or when no hash is stored."""
        if not self.password_hash or not password:
            return False
        return check_password_hash(self.password_hash, password)


class ProfessorProfile(db.Model):
    """Public academic profile for a professor-role user."""

    __tablename__ = "professor_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False
    )
    first_name = db.Column(db.String(80), nullable=True)
    last_name = db.Column(db.String(80), nullable=True)
    title = db.Column(db.String(10), nullable=True)
    rank = db.Column(db.String(40), nullable=True)
    department = db.Column(db.String(120), nullable=False, index=True)
    research_areas = db.Column(db.JSON, nullable=False, default=list)
    bio = db.Column(db.Text, nullable=False, default="")
    rate = db.Column(db.Float, nullable=True)  # whole naira per session
    timezone = db.Column(db.String(64), nullable=False, default="Africa/Lagos")
    availability = db.Column(db.JSON, nullable=False, default=dict)
    accepting_new = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    user = db.relationship("User", back_populates="professor_profile")


class StudentProfile(db.Model):
    """Academic profile for a student-role user."""

    __tablename__ = "student_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False
    )
    level = db.Column(db.String(20), nullable=False)  # undergraduate|masters|phd
    field = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    user = db.relationship("User", back_populates="student_profile")


class Document(db.Model):
    """Student-uploaded file plus its extracted text for agent intake."""

    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    extracted_text = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    student = db.relationship("User", foreign_keys=[student_id])


class CaseFile(db.Model):
    """Agent diagnosis for a student, optionally already routed to a professor."""

    __tablename__ = "case_files"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    professor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    document_id = db.Column(db.Integer, db.ForeignKey("documents.id"), nullable=True)
    problem_text = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="pending")
    run_id = db.Column(db.String(64), nullable=True, index=True)
    grounding_rate = db.Column(db.Float, nullable=True)
    diagnosis = db.Column(db.JSON, nullable=False, default=dict)
    candidate_snapshot = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    student = db.relationship("User", foreign_keys=[student_id])
    professor = db.relationship("User", foreign_keys=[professor_id])


class Booking(db.Model):
    """A requested 60-minute slot; ``scheduled_at`` is the naive-UTC start.

    Status follows the request workflow (see ``booking_workflow``). Only
    active statuses occupy the slot, enforced by a partial unique index.
    """

    __tablename__ = "bookings"
    __table_args__ = (
        db.Index(
            "uq_booking_active_slot",
            "professor_id",
            "scheduled_at",
            unique=True,
            sqlite_where=db.text(
                "status IN ('requested','accepted','reschedule_proposed')"
            ),
            postgresql_where=db.text(
                "status IN ('requested','accepted','reschedule_proposed')"
            ),
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    professor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    case_id = db.Column(db.Integer, db.ForeignKey("case_files.id"), nullable=True)
    idempotency_key = db.Column(db.String(64), nullable=True, unique=True)
    status = db.Column(db.String(20), nullable=False, default="requested")
    scheduled_at = db.Column(db.DateTime, nullable=True)
    decided_at = db.Column(db.DateTime, nullable=True)
    decline_reason = db.Column(db.String(500), nullable=True)
    proposed_start = db.Column(db.DateTime, nullable=True)
    expires_at = db.Column(db.DateTime, nullable=True)
    payment_status = db.Column(db.String(20), nullable=False, default="held")
    meeting_url = db.Column(db.String(500), nullable=True)
    consent_share_diagnosis = db.Column(db.Boolean, nullable=False, default=False)
    mock_payment_ref = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    student = db.relationship("User", foreign_keys=[student_id])
    professor = db.relationship("User", foreign_keys=[professor_id])
    case = db.relationship("CaseFile", foreign_keys=[case_id])
    session_record = db.relationship(
        "SessionRecord",
        back_populates="booking",
        uselist=False,
        cascade="all, delete-orphan",
    )


class SessionRecord(db.Model):
    """Recording consent, transcript, notes and PDF for one booking."""

    __tablename__ = "session_records"

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(
        db.Integer, db.ForeignKey("bookings.id"), unique=True, nullable=False
    )
    consent = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    run_id = db.Column(db.String(64), nullable=True, index=True)
    audio_path = db.Column(db.String(500), nullable=True)
    transcript = db.Column(db.Text, nullable=True)
    turns = db.Column(db.JSON, nullable=True)
    speaker_map = db.Column(db.JSON, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    fidelity_rate = db.Column(db.Float, nullable=True)
    pdf_path = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    booking = db.relationship("Booking", back_populates="session_record")


class MemoryNote(db.Model):
    """Durable per-student progress note, optionally tied to a session."""

    __tablename__ = "memory_notes"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    session_record_id = db.Column(
        db.Integer, db.ForeignKey("session_records.id"), nullable=True
    )
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    student = db.relationship("User", foreign_keys=[student_id])
    session_record = db.relationship("SessionRecord", foreign_keys=[session_record_id])


class RunEvent(db.Model):
    """One step in an agent run timeline, polled live by the case page."""

    __tablename__ = "run_events"

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.String(64), nullable=False, index=True)
    seq = db.Column(db.Integer, nullable=False)
    type = db.Column(db.String(40), nullable=False)
    label = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="ok")
    payload = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)


class MatchResult(db.Model):
    """One ranked professor recommendation for a case (rank 1..3)."""

    __tablename__ = "match_results"

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(
        db.Integer, db.ForeignKey("case_files.id"), nullable=False, index=True
    )
    professor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    rank = db.Column(db.Integer, nullable=False)
    score = db.Column(db.Integer, nullable=False)
    score_flagged = db.Column(db.Boolean, nullable=False, default=False)
    reasons = db.Column(db.JSON, nullable=False, default=list)
    caveats = db.Column(db.JSON, nullable=False, default=list)
    next_slot = db.Column(db.String(200), nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    case = db.relationship("CaseFile", foreign_keys=[case_id])
    professor = db.relationship("User", foreign_keys=[professor_id])


class ClarificationQA(db.Model):
    """One clarifying question (and optional answer) for a case.

    Rows are written when the agent asks; ``answer`` stays NULL when the
    student skips. One round only: no follow-ups reference these rows.
    """

    __tablename__ = "clarification_qas"

    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(
        db.Integer, db.ForeignKey("case_files.id"), nullable=False, index=True
    )
    question_key = db.Column(db.String(20), nullable=False)  # budget|deadline|times|goal
    question = db.Column(db.Text, nullable=False)
    qtype = db.Column(db.String(10), nullable=False)  # choice|text
    options = db.Column(db.JSON, nullable=False, default=list)
    why = db.Column(db.Text, nullable=False, default="")
    gap_ids = db.Column(db.JSON, nullable=False, default=list)
    answer = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    answered_at = db.Column(db.DateTime, nullable=True)

    case = db.relationship("CaseFile", foreign_keys=[case_id])


class EmailLog(db.Model):
    """Audit row for one outbound email; idempotent per booking and kind."""

    __tablename__ = "email_logs"

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(
        db.Integer, db.ForeignKey("bookings.id"), nullable=False, index=True
    )
    kind = db.Column(db.String(40), nullable=False)
    recipient = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    provider = db.Column(db.String(20), nullable=False, default="")
    provider_id = db.Column(db.String(255), nullable=True)
    error = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    booking = db.relationship("Booking", foreign_keys=[booking_id])


class Notification(db.Model):
    """One inbox notification; read when ``read_at`` is set."""

    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    kind = db.Column(db.String(40), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.String(500), nullable=False, default="")
    url = db.Column(db.String(500), nullable=False, default="")
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    read_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", foreign_keys=[user_id])


class LedgerEntry(db.Model):
    """One demo-money movement; balances are computed, never stored.

    ``user_id`` is NULL only for platform_fee rows (the platform's cut).
    Amounts are whole naira, always positive; the type gives the direction.
    """

    __tablename__ = "ledger_entries"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=True, index=True
    )
    booking_id = db.Column(
        db.Integer, db.ForeignKey("bookings.id"), nullable=False, index=True
    )
    type = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    user = db.relationship("User", foreign_keys=[user_id])
    booking = db.relationship("Booking", foreign_keys=[booking_id])


class Message(db.Model):
    """One thread message; read when the other party opens the thread."""

    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(
        db.Integer, db.ForeignKey("bookings.id"), nullable=False, index=True
    )
    sender_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False
    )
    body = db.Column(db.String(2000), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
    read_at = db.Column(db.DateTime, nullable=True)

    booking = db.relationship("Booking", foreign_keys=[booking_id])
    sender = db.relationship("User", foreign_keys=[sender_id])


class ToolCallLog(db.Model):
    """Audit row for every agent tool call (see ``run_tool_loop``)."""

    __tablename__ = "tool_call_logs"

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.String(64), nullable=True, index=True)
    tool_name = db.Column(db.String(120), nullable=False, index=True)
    arguments = db.Column(db.JSON, nullable=False, default=dict)
    result = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="ok")  # ok|error
    error = db.Column(db.Text, nullable=True)
    duration_ms = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)
