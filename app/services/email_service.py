"""Outbound email (stub; provider decision pending).

The Resend-vs-SMTP choice is intentionally deferred to the booking step, when
the professor case-file email is built. This module fixes the interface now so
callers do not need to change later.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmailResult:
    """Outcome of one send attempt."""

    accepted: bool
    message_id: str | None = None


def send_email(
    *,
    to: str,
    subject: str,
    body_text: str,
    body_html: str | None = None,
    from_address: str | None = None,
) -> EmailResult:
    """Send one email; raises until an email provider is configured."""
    raise NotImplementedError(
        "email provider not configured (Resend vs SMTP decision pending)"
    )
