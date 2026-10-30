"""Messaging tests: threads, locks, rate limit, XSS, batching. No network."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from flask import Flask

from app.extensions import db
from app.models import EmailLog, Message, Notification, User
from app.services.messaging import (
    RateLimitedError,
    ThreadLockedError,
    get_threads,
    post_message,
    unread_message_count,
)
from tests.test_booking import login_sample_student, seed_booking_case
from tests.test_professor import login_professor
from tests.test_workflow import force_status, seed_request


def parties(booking_id: int) -> tuple[User, User]:
    """Student and professor users for one booking."""
    from app.models import Booking

    booking = db.session.get(Booking, booking_id)
    assert booking is not None
    student = db.session.get(User, booking.student_id)
    professor = db.session.get(User, booking.professor_id)
    assert student is not None and professor is not None
    return student, professor


def test_post_and_thread_flow(app: Flask) -> None:
    """Both parties post; the thread shows both; opening marks read."""
    booking = seed_request()
    student, professor = parties(booking.id)
    first = post_message(booking.id, student, "Hello, professor.")
    assert first.id is not None
    post_message(booking.id, professor, "Hello! Send chapter two.")
    assert unread_message_count(professor.id) == 1
    client = app.test_client()
    login_professor(client, 12)
    page = client.get(f"/inbox/{booking.id}")
    assert page.status_code == 200
    html = page.get_data(as_text=True)
    assert "Hello, professor." in html and "Send chapter two." in html
    assert unread_message_count(professor.id) == 0
    assert unread_message_count(student.id) == 1
    listing = client.get("/inbox")
    assert listing.status_code == 200
    assert "Sample Student 01" in listing.get_data(as_text=True)


def test_thread_auth(app: Flask) -> None:
    """Anonymous bounces; non-parties 404 on every thread endpoint."""
    from tests.test_intake import login, make_student

    booking = seed_request()
    client = app.test_client()
    assert client.get("/inbox").status_code == 302
    assert client.get(f"/inbox/{booking.id}").status_code == 302
    assert client.get(f"/inbox/{booking.id}/messages").status_code == 302
    assert client.post(f"/inbox/{booking.id}/messages").status_code == 302
    make_student()
    login(client, "intake@example.com")
    assert client.get(f"/inbox/{booking.id}").status_code == 404
    assert client.get(f"/inbox/{booking.id}/messages").status_code == 404
    response = client.post(
        f"/inbox/{booking.id}/messages", data={"body": "hi"}
    )
    assert response.status_code == 404
    assert client.get("/inbox/9999").status_code == 404


def test_post_view_roundtrip(app: Flask) -> None:
    """Form posts 303 to the thread; blank and oversize bodies 400."""
    booking = seed_request()
    client = app.test_client()
    login_sample_student(client)
    created = client.post(
        f"/inbox/{booking.id}/messages", data={"body": "  Hi there.  "}
    )
    assert created.status_code == 303
    assert Message.query.one().body == "Hi there."
    blank = client.post(f"/inbox/{booking.id}/messages", data={"body": "   "})
    assert blank.status_code == 400
    long = client.post(
        f"/inbox/{booking.id}/messages", data={"body": "x" * 2001}
    )
    assert long.status_code == 400
    assert Message.query.count() == 1


@pytest.mark.parametrize(
    "status,allowed",
    [
        ("requested", True),
        ("accepted", True),
        ("reschedule_proposed", True),
        ("declined", False),
        ("cancelled", False),
        ("expired", False),
        ("completed", False),
    ],
)
def test_thread_lock_by_status(app: Flask, status: str, allowed: bool) -> None:
    """Terminal bookings are read-only; active ones accept posts."""
    booking = seed_request()
    force_status(booking, status)
    student, _professor = parties(booking.id)
    client = app.test_client()
    login_sample_student(client)
    response = client.post(
        f"/inbox/{booking.id}/messages", data={"body": "hello"}
    )
    assert response.status_code == (303 if allowed else 403)
    page = client.get(f"/inbox/{booking.id}")
    assert page.status_code == 200
    assert ("read-only" in page.get_data(as_text=True)) is not allowed
    if not allowed:
        with pytest.raises(ThreadLockedError):
            post_message(booking.id, student, "hello")


def test_rate_limit(app: Flask) -> None:
    """The 21st message within a minute is refused with 429."""
    booking = seed_request()
    client = app.test_client()
    login_sample_student(client)
    url = f"/inbox/{booking.id}/messages"
    for number in range(20):
        assert client.post(url, data={"body": f"m{number}"}).status_code == 303
    limited = client.post(url, data={"body": "one too many"})
    assert limited.status_code == 429
    assert "too many" in limited.get_data(as_text=True).lower()
    student, _professor = parties(booking.id)
    with pytest.raises(RateLimitedError):
        post_message(booking.id, student, "nope")
    old = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
        minutes=2
    )
    Message.query.update({"created_at": old})
    db.session.commit()
    assert client.post(url, data={"body": "after window"}).status_code == 303


def test_xss_escaped_in_html_raw_in_json(app: Flask) -> None:
    """Markup is escaped in pages; JSON stays raw (client uses textContent)."""
    booking = seed_request()
    student, _professor = parties(booking.id)
    post_message(booking.id, student, '<script>alert("x")</script>')
    client = app.test_client()
    login_sample_student(client)
    html = client.get(f"/inbox/{booking.id}").get_data(as_text=True)
    assert "<script>alert" not in html
    assert "&lt;script&gt;" in html
    payload = client.get(f"/inbox/{booking.id}/messages").get_json()
    assert payload["messages"][0]["body"] == '<script>alert("x")</script>'


def test_poll_after_filter(app: Flask) -> None:
    """The poll endpoint returns only messages after the cursor."""
    booking = seed_request()
    student, professor = parties(booking.id)
    first = post_message(booking.id, student, "one")
    post_message(booking.id, professor, "two")
    client = app.test_client()
    login_sample_student(client)
    payload = client.get(
        f"/inbox/{booking.id}/messages?after={first.id}"
    ).get_json()
    assert [item["body"] for item in payload["messages"]] == ["two"]
    assert payload["messages"][0]["mine"] is False
    assert client.get(
        f"/inbox/{booking.id}/messages?after=bogus"
    ).get_json()["messages"] != []


def test_notification_batching(app: Flask) -> None:
    """One ping per thread per 10 minutes, then a fresh one."""
    booking = seed_request()
    client = app.test_client()
    login_sample_student(client)
    url = f"/inbox/{booking.id}/messages"
    client.post(url, data={"body": "first"})
    client.post(url, data={"body": "second"})
    _student, professor = parties(booking.id)
    assert Notification.query.filter_by(user_id=professor.id).count() == 1
    old = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
        minutes=11
    )
    Notification.query.update({"created_at": old})
    db.session.commit()
    client.post(url, data={"body": "third"})
    assert Notification.query.filter_by(user_id=professor.id).count() == 2


def test_email_batching(app: Flask) -> None:
    """One ping email per thread per hour through the idempotent service."""
    booking = seed_request()
    client = app.test_client()
    login_sample_student(client)
    url = f"/inbox/{booking.id}/messages"
    client.post(url, data={"body": "first"})
    client.post(url, data={"body": "second"})
    assert EmailLog.query.filter_by(booking_id=booking.id).count() == 1
    old = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
        minutes=61
    )
    EmailLog.query.update(
        {"created_at": old, "kind": "new_message:20000101T00"}
    )
    db.session.commit()
    client.post(url, data={"body": "third"})
    assert EmailLog.query.filter_by(booking_id=booking.id).count() == 2


def test_message_links_present(app: Flask) -> None:
    """Both roles link to the thread from sessions, confirmation, files."""
    booking = seed_request()
    client = app.test_client()
    login_sample_student(client)
    thread_url = f"/inbox/{booking.id}"
    assert thread_url in client.get(
        f"/sessions/{booking.id}"
    ).get_data(as_text=True)
    assert thread_url in client.get(
        f"/sessions/{booking.id}/confirmation"
    ).get_data(as_text=True)
    login_professor(client, 12)
    assert thread_url in client.get(
        f"/dashboard/bookings/{booking.id}"
    ).get_data(as_text=True)


def test_workspace_inbox_tab_lists_threads(app: Flask) -> None:
    """The professor workspace shows threads with unread counts."""
    booking = seed_request()
    student, _professor = parties(booking.id)
    post_message(booking.id, student, "Question about Friday.")
    client = app.test_client()
    login_professor(client, 12)
    html = client.get("/dashboard?tab=inbox").get_data(as_text=True)
    assert "Question about Friday." in html
    assert "1 new" in html
    assert "Unread messages" in html
