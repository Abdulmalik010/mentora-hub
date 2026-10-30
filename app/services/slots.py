"""60-minute booking slots from weekly availability patterns.

Availability is stored per professor as ``{"days": [...], "hours": "10:00-14:00
WAT"}``. Slots are generated in Africa/Lagos time, stored naive UTC (the
project datetime convention), and displayed in WAT with a local-time hint.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

WAT = ZoneInfo("Africa/Lagos")
SLOT_MINUTES = 60
SLOT_DAYS_AHEAD = 14
WEEKDAYS = (
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
    "Sunday",
)


@dataclass(frozen=True)
class Slot:
    """One bookable hour; ``start_utc`` is tz-aware, ``key`` is the form value."""

    start_utc: datetime

    @property
    def end_utc(self) -> datetime:
        """Slot end (fixed 60-minute duration)."""
        return self.start_utc + timedelta(minutes=SLOT_MINUTES)

    @property
    def start_wat(self) -> datetime:
        """Slot start rendered in Africa/Lagos time."""
        return self.start_utc.astimezone(WAT)

    @property
    def end_wat(self) -> datetime:
        """Slot end rendered in Africa/Lagos time."""
        return self.end_utc.astimezone(WAT)

    @property
    def start_naive_utc(self) -> datetime:
        """Persistence form: naive UTC for the SQLite column."""
        return self.start_utc.astimezone(timezone.utc).replace(tzinfo=None)

    @property
    def key(self) -> str:
        """Stable form value round-tripping through :func:`slot_from_key`."""
        return self.start_utc.astimezone(timezone.utc).isoformat()


def slot_from_key(key: str) -> Slot | None:
    """Rebuild a slot from a submitted key; None when malformed."""
    try:
        start = datetime.fromisoformat(key)
    except (TypeError, ValueError):
        return None
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    return Slot(start_utc=start.astimezone(timezone.utc))


def parse_hours(hours: str) -> tuple[time, time] | None:
    """Parse ``"10:00-14:00 WAT"`` into open/close times (None when bad)."""
    span = (hours or "").removesuffix("WAT").strip()
    try:
        open_text, close_text = span.split("-", 1)
        opens = time.fromisoformat(open_text.strip())
        closes = time.fromisoformat(close_text.strip())
    except ValueError:
        return None
    if opens >= closes:
        return None
    return opens, closes


def availability_windows(
    availability: Mapping[str, Any] | None,
) -> list[tuple[time, time]]:
    """Weekly time windows, newest format first, legacy fallback last.

    Current shape is ``{"days": [...], "windows": [["10:00", "14:00"]]}``;
    the legacy ``"hours": "10:00-14:00 WAT"`` string still parses. Empty
    or malformed availability yields no windows.
    """
    data = availability or {}
    windows = data.get("windows") or []
    parsed: list[tuple[time, time]] = []
    for window in windows:
        try:
            opens = time.fromisoformat(str(window[0]))
            closes = time.fromisoformat(str(window[1]))
        except (IndexError, TypeError, ValueError):
            continue
        if opens < closes:
            parsed.append((opens, closes))
    if parsed:
        return parsed
    legacy = parse_hours(str(data.get("hours", "") or ""))
    return [legacy] if legacy else []


def validate_availability(
    days: list[str], windows: list[tuple[str, str]]
) -> list[str]:
    """Check editor input; return human-readable errors (empty means valid).

    Days must be real weekday names, windows must be whole-hour ``HH:MM``
    pairs with start before end, and windows must not overlap (the slot
    grid is hourly, so sub-hour precision would silently mislead).
    """
    errors = []
    if not days:
        errors.append("pick at least one day")
    for day in days:
        if day not in WEEKDAYS:
            errors.append(f"unknown day: {day}")
    spans: list[tuple[time, time]] = []
    for opens_text, closes_text in windows:
        try:
            opens = time.fromisoformat(opens_text)
            closes = time.fromisoformat(closes_text)
        except ValueError:
            errors.append(f"bad time window: {opens_text}-{closes_text}")
            continue
        if opens.minute or closes.minute or opens.second or closes.second:
            errors.append(
                f"window {opens_text}-{closes_text} must start and end "
                "on the hour"
            )
            continue
        if opens >= closes:
            errors.append(
                f"window {opens_text}-{closes_text} ends before it starts"
            )
            continue
        spans.append((opens, closes))
    if not spans and not errors:
        errors.append("add at least one time window")
    for first, second in zip(sorted(spans), sorted(spans)[1:]):
        if first[1] > second[0]:
            errors.append("time windows must not overlap")
            break
    return errors


def generate_slots(
    availability: Mapping[str, Any] | None,
    *,
    days_ahead: int = SLOT_DAYS_AHEAD,
    now: datetime | None = None,
) -> list[Slot]:
    """Concrete future slots for the next ``days_ahead`` days (offsets 1..N).

    Only whole hours inside the open window on listed weekdays; past slots
    are dropped. Empty or malformed availability yields no slots.
    """
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    days = set((availability or {}).get("days", []) or [])
    windows = availability_windows(availability)
    if not days or not windows:
        return []
    today_wat = current.astimezone(WAT).date()
    slots: list[Slot] = []
    for offset in range(1, max(1, days_ahead) + 1):
        day: date = today_wat + timedelta(days=offset)
        if day.strftime("%A") not in days:
            continue
        for opens, closes in windows:
            closes_at = datetime(
                day.year, day.month, day.day, closes.hour, closes.minute,
                tzinfo=WAT,
            )
            hour = opens.hour + (1 if opens.minute else 0)
            while hour < 24:
                start_wat = datetime(
                    day.year, day.month, day.day, hour, tzinfo=WAT
                )
                if start_wat + timedelta(minutes=SLOT_MINUTES) > closes_at:
                    break
                start_utc = start_wat.astimezone(timezone.utc)
                if start_utc > current:
                    slots.append(Slot(start_utc=start_utc))
                hour += 1
    slots.sort(key=lambda slot: slot.start_utc)
    return slots


def format_wat(moment: datetime) -> str:
    """Naive-UTC (or aware) datetime as ``"Mon, Nov 3 · 10:00 WAT"``."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    wat = moment.astimezone(WAT)
    return f"{wat.strftime('%a, %b')} {wat.day} · {wat.strftime('%H:%M')} WAT"
