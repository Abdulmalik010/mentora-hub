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
    window = parse_hours(str((availability or {}).get("hours", "") or ""))
    if not days or window is None:
        return []
    opens, closes = window
    today_wat = current.astimezone(WAT).date()
    slots: list[Slot] = []
    for offset in range(1, max(1, days_ahead) + 1):
        day: date = today_wat + timedelta(days=offset)
        if day.strftime("%A") not in days:
            continue
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
    return slots


def format_wat(moment: datetime) -> str:
    """Naive-UTC (or aware) datetime as ``"Mon, Nov 3 · 10:00 WAT"``."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    wat = moment.astimezone(WAT)
    return f"{wat.strftime('%a, %b')} {wat.day} · {wat.strftime('%H:%M')} WAT"
