"""Schedules: manual, every 15 minutes, hourly, daily."""

from __future__ import annotations

from datetime import datetime, timedelta

INTERVALS = {"15m": timedelta(minutes=15), "hourly": timedelta(hours=1), "daily": timedelta(days=1)}
LABELS = {"manual": "Manual", "15m": "Every 15 minutes", "hourly": "Hourly", "daily": "Daily"}


def next_run_after(schedule: str, moment: datetime) -> datetime | None:
    interval = INTERVALS.get(schedule)
    return moment + interval if interval else None
