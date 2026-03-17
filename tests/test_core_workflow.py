import asyncio
from datetime import datetime

import pytest

from src.backend.core import run_appointment_happy_path


class FakeConn:
    def __init__(self):
        self.calls = []

    async def execute(self, query, *args):
        self.calls.append((query, args))


def test_run_appointment_happy_path_persists_valid_window():
    conn = FakeConn()
    start_time = datetime(2026, 1, 10, 10, 0, 0)
    end_time = datetime(2026, 1, 10, 11, 0, 0)

    result = asyncio.run(
        run_appointment_happy_path(conn, "  Haircut  ", start_time, end_time)
    )

    assert result.title == "Haircut"
    assert result.start_time == start_time
    assert result.end_time == end_time
    assert conn.calls == [
        (
            "INSERT INTO appointments (title, start_time, end_time) VALUES ($1, $2, $3)",
            ("Haircut", start_time, end_time),
        )
    ]


def test_run_appointment_happy_path_rejects_invalid_time_range():
    conn = FakeConn()
    start_time = datetime(2026, 1, 10, 11, 0, 0)
    end_time = datetime(2026, 1, 10, 10, 0, 0)

    with pytest.raises(ValueError, match="end_time must be after start_time"):
        asyncio.run(run_appointment_happy_path(conn, "Haircut", start_time, end_time))

    assert conn.calls == []
