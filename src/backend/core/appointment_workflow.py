"""Core helpers for the sample appointment workflow."""

from dataclasses import dataclass
from datetime import datetime, time
from typing import Protocol

BUSINESS_HOUR_START = time(9, 0, 0)
BUSINESS_HOUR_END = time(17, 0, 0)


@dataclass(frozen=True, slots=True)
class AppointmentRecord:
    """Normalized appointment payload used across the sample layers."""

    title: str
    start_time: datetime
    end_time: datetime


class AppointmentWriteConnection(Protocol):
    """Minimal async database interface required by core appointment helpers."""

    async def execute(self, query: str, *args: object) -> object: ...

    async def fetch(self, query: str, *args: object) -> list[object]: ...


def _normalize_title(title: str) -> str:
    if not isinstance(title, str):
        raise ValueError("title must be a string")

    normalized_title = " ".join(title.split())
    if not normalized_title:
        raise ValueError("title must not be empty")
    return normalized_title


def prepare_appointment_record(
    title: str, start_time: datetime, end_time: datetime
) -> AppointmentRecord:
    """Normalize appointment input and enforce the sample business rules."""
    if not isinstance(start_time, datetime):
        raise ValueError("start_time must be a datetime")
    if not isinstance(end_time, datetime):
        raise ValueError("end_time must be a datetime")

    normalized_title = _normalize_title(title)

    if end_time <= start_time:
        raise ValueError("end_time must be after start_time")
    if start_time.date() != end_time.date():
        raise ValueError("appointment must start and end on the same day")
    if (
        start_time.time() < BUSINESS_HOUR_START
        or end_time.time() > BUSINESS_HOUR_END
    ):
        raise ValueError("appointment must be within business hours (09:00-17:00)")

    return AppointmentRecord(
        title=normalized_title,
        start_time=start_time,
        end_time=end_time,
    )


async def _has_conflict(
    conn: AppointmentWriteConnection, start_time: datetime, end_time: datetime
) -> bool:
    rows = await conn.fetch(
        """
        SELECT 1
        FROM appointments
        WHERE start_time < $2 AND end_time > $1
        LIMIT 1
        """,
        start_time,
        end_time,
    )
    return bool(rows)


async def run_appointment_happy_path(
    conn: AppointmentWriteConnection,
    title: str,
    start_time: datetime,
    end_time: datetime,
) -> AppointmentRecord:
    """Validate and persist an appointment in the sample happy path flow."""
    appointment = prepare_appointment_record(title, start_time, end_time)
    if await _has_conflict(conn, appointment.start_time, appointment.end_time):
        raise ValueError("appointment conflicts with an existing booking")

    await conn.execute(
        "INSERT INTO appointments (title, start_time, end_time) VALUES ($1, $2, $3)",
        appointment.title,
        appointment.start_time,
        appointment.end_time,
    )
    return appointment


__all__ = [
    "AppointmentRecord",
    "AppointmentWriteConnection",
    "BUSINESS_HOUR_END",
    "BUSINESS_HOUR_START",
    "prepare_appointment_record",
    "run_appointment_happy_path",
]
