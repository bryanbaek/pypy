from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class AppointmentWindow:
    title: str
    start_time: datetime
    end_time: datetime


def validate_appointment_window(
    title: str, start_time: datetime, end_time: datetime
) -> AppointmentWindow:
    normalized_title = title.strip()
    if not normalized_title:
        raise ValueError("title must not be empty")

    if end_time <= start_time:
        raise ValueError("end_time must be after start_time")

    return AppointmentWindow(
        title=normalized_title, start_time=start_time, end_time=end_time
    )


async def run_appointment_happy_path(
    conn, title: str, start_time: datetime, end_time: datetime
) -> AppointmentWindow:
    window = validate_appointment_window(title, start_time, end_time)
    await conn.execute(
        "INSERT INTO appointments (title, start_time, end_time) VALUES ($1, $2, $3)",
        window.title,
        window.start_time,
        window.end_time,
    )
    return window


__all__ = [
    "AppointmentWindow",
    "run_appointment_happy_path",
    "validate_appointment_window",
]
