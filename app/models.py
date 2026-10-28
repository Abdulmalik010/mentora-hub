"""SQLAlchemy models for Mentora Academic Hub (scaffold v1).

Tables are created with ``db.create_all()``; no migrations until the schema
stabilizes after the auth step. Roles, statuses and levels are plain strings
(see DECISIONS.md); datetimes are naive UTC (SQLite limitation).
"""
from __future__ import annotations

from datetime import datetime, timezone

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


class ProfessorProfile(db.Model):
    """Public academic profile for a professor-role user."""

    __tablename__ = "professor_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False
    )
    department = db.Column(db.String(120), nullable=False, index=True)
    research_areas = db.Column(db.JSON, nullable=False, default=list)
    bio = db.Column(db.Text, nullable=False, default="")
    rate = db.Column(db.Float, nullable=True)  # unit decided at booking step
    timezone = db.Column(db.String(64), nullable=False, default="Africa/Lagos")
    availability = db.Column(db.JSON, nullable=False, default=dict)
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
    diagnosis = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    student = db.relationship("User", foreign_keys=[student_id])
    professor = db.relationship("User", foreign_keys=[professor_id])


class Booking(db.Model):
    """A booked slot between a student and a professor; payment is mocked."""

    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    professor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending")
    scheduled_at = db.Column(db.DateTime, nullable=True)
    mock_payment_ref = db.Column(db.String(120), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    student = db.relationship("User", foreign_keys=[student_id])
    professor = db.relationship("User", foreign_keys=[professor_id])
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
    transcript = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
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
