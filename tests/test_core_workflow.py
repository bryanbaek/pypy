import asyncio
from datetime import datetime

import pytest

from src.backend.core import run_appointment_happy_path


class FakeConn:
    def __init__(self, existing=None):
        self.calls = []
        self.existing = existing or []

    async def execute(self, query, *args):
        self.calls.append((query, args))

    async def fetch(self, query, *args):
        self.calls.append((query, args))
        start_time, end_time = args
        for existing_start, existing_end in self.existing:
            if existing_start < end_time and existing_end > start_time:
                return [1]
        return []


def test_run_appointment_happy_path_persists_valid_window():
    conn = FakeConn()
    start_time = datetime(2026, 1, 10, 10, 0, 0)
    end_time = datetime(2026, 1, 10, 11, 0, 0)

    result = asyncio.run(
        run_appointment_happy_path(
            conn, "  Haircut   Appointment  ", start_time, end_time
        )
    )

    assert result.title == "Haircut Appointment"
    assert result.start_time == start_time
    assert result.end_time == end_time
    assert len(conn.calls) == 2
    assert "FROM appointments" in conn.calls[0][0]
    assert conn.calls[0][1] == (start_time, end_time)
    assert conn.calls[1] == (
        "INSERT INTO appointments (title, start_time, end_time) VALUES ($1, $2, $3)",
        ("Haircut Appointment", start_time, end_time),
    )


def test_run_appointment_happy_path_rejects_invalid_time_range():
    conn = FakeConn()
    start_time = datetime(2026, 1, 10, 11, 0, 0)
    end_time = datetime(2026, 1, 10, 10, 0, 0)

    with pytest.raises(ValueError, match="end_time must be after start_time"):
        asyncio.run(run_appointment_happy_path(conn, "Haircut", start_time, end_time))

    assert conn.calls == []


def test_run_appointment_happy_path_rejects_outside_business_hours():
    conn = FakeConn()
    start_time = datetime(2026, 1, 10, 8, 30, 0)
    end_time = datetime(2026, 1, 10, 9, 30, 0)

    with pytest.raises(
        ValueError, match="appointment must be within business hours \\(09:00-17:00\\)"
    ):
        asyncio.run(run_appointment_happy_path(conn, "Haircut", start_time, end_time))

    assert conn.calls == []


def test_run_appointment_happy_path_rejects_conflicting_window():
    existing_start = datetime(2026, 1, 10, 10, 30, 0)
    existing_end = datetime(2026, 1, 10, 11, 30, 0)
    conn = FakeConn(existing=[(existing_start, existing_end)])
    start_time = datetime(2026, 1, 10, 10, 0, 0)
    end_time = datetime(2026, 1, 10, 11, 0, 0)

    with pytest.raises(
        ValueError, match="appointment conflicts with an existing booking"
    ):
        asyncio.run(run_appointment_happy_path(conn, "Haircut", start_time, end_time))

    assert len(conn.calls) == 1
    assert "FROM appointments" in conn.calls[0][0]
