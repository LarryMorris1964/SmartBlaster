from datetime import datetime

from smartblaster.events.sources import CompositeEventSource, DailyTimeEventSource, QueueEventSource, WeeklyTimeEventSource


def test_daily_time_event_source_fires_on_and_off_once_per_day() -> None:
    src = DailyTimeEventSource(on_time="10:00", off_time="16:00")

    assert src.poll(now=datetime(2026, 3, 15, 9, 59)) is None
    assert src.poll(now=datetime(2026, 3, 15, 10, 0)) == "cool_requested"
    assert src.poll(now=datetime(2026, 3, 15, 10, 30)) is None

    assert src.poll(now=datetime(2026, 3, 15, 16, 0)) == "stop_requested"
    assert src.poll(now=datetime(2026, 3, 15, 16, 30)) is None

    # Next day should fire again.
    assert src.poll(now=datetime(2026, 3, 16, 10, 0)) == "cool_requested"
    assert src.poll(now=datetime(2026, 3, 16, 16, 0)) == "stop_requested"


def test_daily_time_event_source_respects_active_days() -> None:
    src = DailyTimeEventSource(
        on_time="10:00",
        off_time="16:00",
        active_days=("mon", "tue", "wed", "thu", "fri"),
    )

    # Saturday should not trigger schedule events.
    assert src.poll(now=datetime(2026, 3, 14, 10, 0)) is None

    # Monday should trigger schedule events.
    assert src.poll(now=datetime(2026, 3, 16, 10, 0)) == "cool_requested"


def test_queue_event_source() -> None:
    src = QueueEventSource()
    assert src.poll() is None

    src.push("cool_requested")
    src.push("stop_requested")

    assert src.poll() == "cool_requested"
    assert src.poll() == "stop_requested"
    assert src.poll() is None


def test_composite_event_source_returns_first_available_event() -> None:
    queue1 = QueueEventSource()
    queue2 = QueueEventSource()

    queue2.push("cool_requested")
    composite = CompositeEventSource(sources=[queue1, queue2])

    assert composite.poll() == "cool_requested"
    assert composite.poll() is None


def test_weekly_time_event_source_uses_per_day_schedule() -> None:
    src = WeeklyTimeEventSource(
        schedule_by_day={
            "mon": {"on_time": "09:30", "off_time": "14:45"},
            "tue": {"on_time": "10:15", "off_time": "15:15"},
        }
    )

    # Monday schedule.
    assert src.poll(now=datetime(2026, 3, 16, 9, 29)) is None
    assert src.poll(now=datetime(2026, 3, 16, 9, 30)) == "cool_requested"
    assert src.poll(now=datetime(2026, 3, 16, 14, 45)) == "stop_requested"

    # Tuesday schedule.
    assert src.poll(now=datetime(2026, 3, 17, 10, 15)) == "cool_requested"
    assert src.poll(now=datetime(2026, 3, 17, 15, 15)) == "stop_requested"


def test_weekly_time_event_source_skips_unconfigured_day() -> None:
    src = WeeklyTimeEventSource(
        schedule_by_day={"mon": {"on_time": "10:00", "off_time": "15:00"}}
    )
    # Tuesday has no schedule entry.
    assert src.poll(now=datetime(2026, 3, 17, 10, 0)) is None
