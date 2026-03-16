"""Event source abstractions for scheduler and external stimuli."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Protocol
from zoneinfo import ZoneInfo

_WEEKDAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


class EventSource(Protocol):
    def poll(self, *, now: datetime | None = None) -> str | None:
        """Return the next event, or None when no event is ready."""


@dataclass
class DailyTimeEventSource:
    """Generates daily `cool_requested` and `stop_requested` events at fixed times."""

    on_time: str = "10:00"
    off_time: str = "15:00"
    active_days: tuple[str, ...] = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
    timezone: str = "UTC"
    _weekly: "WeeklyTimeEventSource" | None = field(default=None, init=False, repr=False)

    @staticmethod
    def _minutes_since_midnight(value: str) -> int:
        hours_str, minutes_str = value.strip().split(":", 1)
        hours = int(hours_str)
        minutes = int(minutes_str)
        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            raise ValueError(f"invalid time: {value}")
        return hours * 60 + minutes

    def _local_now(self, now: datetime | None) -> datetime:
        if now is not None:
            return now
        return datetime.now(ZoneInfo(self.timezone))

    @staticmethod
    def _weekday_key(value: datetime) -> str:
        return _WEEKDAY_KEYS[value.weekday()]

    def poll(self, *, now: datetime | None = None) -> str | None:
        if self._weekly is None:
            schedule = {
                day: {"on_time": self.on_time, "off_time": self.off_time}
                for day in self.active_days
            }
            self._weekly = WeeklyTimeEventSource(schedule_by_day=schedule, timezone=self.timezone)
        return self._weekly.poll(now=now)


@dataclass
class WeeklyTimeEventSource:
    """Generates events using per-day schedule entries.

    `schedule_by_day` keys are weekday tokens (mon..sun) and values are maps with
    `on_time` and `off_time` formatted as HH:MM.
    """

    schedule_by_day: dict[str, dict[str, str]]
    timezone: str = "UTC"
    _on_fired_date: date | None = None
    _off_fired_date: date | None = None

    def _local_now(self, now: datetime | None) -> datetime:
        if now is not None:
            return now
        return datetime.now(ZoneInfo(self.timezone))

    @staticmethod
    def _weekday_key(value: datetime) -> str:
        return _WEEKDAY_KEYS[value.weekday()]

    def poll(self, *, now: datetime | None = None) -> str | None:
        current = self._local_now(now)
        weekday = self._weekday_key(current)
        day_schedule = self.schedule_by_day.get(weekday)
        if not day_schedule:
            return None

        today = current.date()
        current_minutes = current.hour * 60 + current.minute

        on_time = str(day_schedule.get("on_time", "")).strip()
        off_time = str(day_schedule.get("off_time", "")).strip()
        on_minutes = DailyTimeEventSource._minutes_since_midnight(on_time)
        off_minutes = DailyTimeEventSource._minutes_since_midnight(off_time)

        if self._on_fired_date != today and current_minutes >= on_minutes:
            self._on_fired_date = today
            return "cool_requested"

        if self._off_fired_date != today and current_minutes >= off_minutes:
            self._off_fired_date = today
            return "stop_requested"

        return None


@dataclass
class QueueEventSource:
    """In-memory queue for external events (future solar/inverter integration)."""

    _queue: deque[str] = field(default_factory=deque)

    def push(self, event: str) -> None:
        self._queue.append(event)

    def poll(self, *, now: datetime | None = None) -> str | None:  # noqa: ARG002
        if not self._queue:
            return None
        return self._queue.popleft()


@dataclass
class CompositeEventSource:
    """Polls multiple event sources in order and returns the first available event."""

    sources: list[EventSource]

    def poll(self, *, now: datetime | None = None) -> str | None:
        for source in self.sources:
            event = source.poll(now=now)
            if event:
                return event
        return None
