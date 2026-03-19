import asyncio
from datetime import datetime

import pytest

from src.backend.core import run_appointment_happy_path
from src.backend.db.postgres import create_appointment


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


def test_run_appointment_happy_path_rejects_after_business_hours():
    conn = FakeConn()
    start_time = datetime(2026, 1, 10, 16, 30, 0)
    end_time = datetime(2026, 1, 10, 17, 30, 0)

    with pytest.raises(
        ValueError, match="appointment must be within business hours \\(09:00-17:00\\)"
    ):
        asyncio.run(run_appointment_happy_path(conn, "Haircut", start_time, end_time))

    assert conn.calls == []


def test_run_appointment_happy_path_allows_business_hour_boundaries():
    conn = FakeConn()
    start_time = datetime(2026, 1, 10, 9, 0, 0)
    end_time = datetime(2026, 1, 10, 17, 0, 0)

    result = asyncio.run(
        run_appointment_happy_path(
            conn, "   All   Day   Session   ", start_time, end_time
        )
    )

    assert result.title == "All Day Session"
    assert result.start_time == start_time
    assert result.end_time == end_time
    assert len(conn.calls) == 2
    assert conn.calls[1][1] == ("All Day Session", start_time, end_time)


def test_run_appointment_happy_path_rejects_cross_day_window():
    conn = FakeConn()
    start_time = datetime(2026, 1, 10, 16, 0, 0)
    end_time = datetime(2026, 1, 11, 10, 0, 0)

    with pytest.raises(
        ValueError, match="appointment must start and end on the same day"
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


def test_run_appointment_happy_path_allows_edge_aligned_non_overlapping_window():
    existing_start = datetime(2026, 1, 10, 10, 0, 0)
    existing_end = datetime(2026, 1, 10, 11, 0, 0)
    conn = FakeConn(existing=[(existing_start, existing_end)])
    start_time = datetime(2026, 1, 10, 11, 0, 0)
    end_time = datetime(2026, 1, 10, 12, 0, 0)

    result = asyncio.run(
        run_appointment_happy_path(conn, " Follow Up ", start_time, end_time)
    )

    assert result.title == "Follow Up"
    assert len(conn.calls) == 2
    assert "FROM appointments" in conn.calls[0][0]
    assert conn.calls[1][1] == ("Follow Up", start_time, end_time)


def test_run_appointment_happy_path_rejects_empty_normalized_title():
    conn = FakeConn()
    start_time = datetime(2026, 1, 10, 10, 0, 0)
    end_time = datetime(2026, 1, 10, 11, 0, 0)

    with pytest.raises(ValueError, match="title must not be empty"):
        asyncio.run(run_appointment_happy_path(conn, "   \t   ", start_time, end_time))

    assert conn.calls == []


def test_run_appointment_happy_path_rejects_non_string_title():
    conn = FakeConn()
    start_time = datetime(2026, 1, 10, 10, 0, 0)
    end_time = datetime(2026, 1, 10, 11, 0, 0)

    with pytest.raises(ValueError, match="title must be a string"):
        asyncio.run(run_appointment_happy_path(conn, 123, start_time, end_time))

    assert conn.calls == []


def test_run_appointment_happy_path_normalizes_multiline_whitespace():
    conn = FakeConn()
    start_time = datetime(2026, 1, 10, 13, 0, 0)
    end_time = datetime(2026, 1, 10, 14, 0, 0)

    result = asyncio.run(
        run_appointment_happy_path(
            conn, "  Intake \n\t Consultation   Session  ", start_time, end_time
        )
    )

    assert result.title == "Intake Consultation Session"
    assert len(conn.calls) == 2
    assert conn.calls[1][1] == ("Intake Consultation Session", start_time, end_time)


def test_create_appointment_applies_happy_path_validation_and_normalization():
    conn = FakeConn()
    start_time = datetime(2026, 1, 10, 10, 0, 0)
    end_time = datetime(2026, 1, 10, 11, 0, 0)

    result = asyncio.run(
        create_appointment(conn, "  New   Client\n Intake  ", start_time, end_time)
    )

    assert result.title == "New Client Intake"
    assert result.start_time == start_time
    assert result.end_time == end_time
    assert len(conn.calls) == 2
    assert "FROM appointments" in conn.calls[0][0]
    assert conn.calls[1][1] == ("New Client Intake", start_time, end_time)


def test_create_appointment_rejects_conflicting_windows_via_core_validation():
    existing_start = datetime(2026, 1, 10, 10, 30, 0)
    existing_end = datetime(2026, 1, 10, 11, 30, 0)
    conn = FakeConn(existing=[(existing_start, existing_end)])
    start_time = datetime(2026, 1, 10, 10, 0, 0)
    end_time = datetime(2026, 1, 10, 11, 0, 0)

    with pytest.raises(
        ValueError, match="appointment conflicts with an existing booking"
    ):
        asyncio.run(create_appointment(conn, "Haircut", start_time, end_time))

    assert len(conn.calls) == 1


def test_create_appointment_rejects_outside_business_hours_via_core_validation():
    conn = FakeConn()
    start_time = datetime(2026, 1, 10, 8, 59, 0)
    end_time = datetime(2026, 1, 10, 9, 30, 0)

    with pytest.raises(
        ValueError, match="appointment must be within business hours \\(09:00-17:00\\)"
    ):
        asyncio.run(create_appointment(conn, "Haircut", start_time, end_time))

    assert conn.calls == []
