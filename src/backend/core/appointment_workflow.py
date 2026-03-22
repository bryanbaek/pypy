"""Core validation helpers for the sample appointment workflow."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class AppointmentRecord:
    """Normalized appointment payload used by controller orchestration."""

    title: str
    start_time: datetime
    end_time: datetime


def prepare_appointment_record(
    title: str,
    start_time: datetime,
    end_time: datetime,
) -> AppointmentRecord:
    """Normalize an appointment payload before it reaches the gateway layer."""
    normalized_title = title.strip()
    if not normalized_title:
        raise ValueError("title must not be empty")
    if end_time <= start_time:
        raise ValueError("end_time must be after start_time")

    return AppointmentRecord(
        title=normalized_title,
        start_time=start_time,
        end_time=end_time,
    )


__all__ = ["AppointmentRecord", "prepare_appointment_record"]
