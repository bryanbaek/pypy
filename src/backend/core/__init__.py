from dataclasses import dataclass
from datetime import datetime, time


@dataclass(frozen=True, slots=True)
class AppointmentWindow:
    title: str
    start_time: datetime
    end_time: datetime


BUSINESS_HOUR_START = time(9, 0)
BUSINESS_HOUR_END = time(17, 0)


def normalize_appointment_title(title: str) -> str:
    return " ".join(title.split())


def validate_appointment_time_window(start_time: datetime, end_time: datetime) -> None:
    if end_time <= start_time:
        raise ValueError("end_time must be after start_time")

    if start_time.date() != end_time.date():
        raise ValueError("appointment must start and end on the same day")

    start_tod = start_time.time()
    end_tod = end_time.time()
    if start_tod < BUSINESS_HOUR_START or end_tod > BUSINESS_HOUR_END:
        raise ValueError("appointment must be within business hours (09:00-17:00)")


def validate_appointment_window(
    title: str, start_time: datetime, end_time: datetime
) -> AppointmentWindow:
    normalized_title = normalize_appointment_title(title)
    if not normalized_title:
        raise ValueError("title must not be empty")

    validate_appointment_time_window(start_time, end_time)

    return AppointmentWindow(
        title=normalized_title, start_time=start_time, end_time=end_time
    )


async def has_appointment_conflict(
    conn, start_time: datetime, end_time: datetime
) -> bool:
    conflicting = await conn.fetch(
        """
        SELECT 1
        FROM appointments
        WHERE start_time < $2
          AND end_time > $1
        LIMIT 1
        """,
        start_time,
        end_time,
    )
    return bool(conflicting)


async def run_appointment_happy_path(
    conn, title: str, start_time: datetime, end_time: datetime
) -> AppointmentWindow:
    window = validate_appointment_window(title, start_time, end_time)
    if await has_appointment_conflict(conn, window.start_time, window.end_time):
        raise ValueError("appointment conflicts with an existing booking")

    await conn.execute(
        "INSERT INTO appointments (title, start_time, end_time) VALUES ($1, $2, $3)",
        window.title,
        window.start_time,
        window.end_time,
    )
    return window


__all__ = [
    "AppointmentWindow",
    "BUSINESS_HOUR_END",
    "BUSINESS_HOUR_START",
    "has_appointment_conflict",
    "normalize_appointment_title",
    "run_appointment_happy_path",
    "validate_appointment_time_window",
    "validate_appointment_window",
]
