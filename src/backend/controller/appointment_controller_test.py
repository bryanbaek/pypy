"""Tests for appointment controller validation workflow."""

import asyncio
from datetime import datetime

import pytest

from src.backend.controller.appointment_controller import AppointmentController


class StubAppointmentGateway:
    def __init__(self) -> None:
        self.conflict = False
        self.conflict_checks: list[tuple[datetime, datetime, int | None]] = []
        self.created: tuple[str, datetime, datetime] | None = None

    async def has_conflict(
        self,
        start_time: datetime,
        end_time: datetime,
        exclude_appointment_id: int | None = None,
    ) -> bool:
        self.conflict_checks.append((start_time, end_time, exclude_appointment_id))
        return self.conflict

    async def create_appointment(
        self, title: str, start_time: datetime, end_time: datetime
    ) -> dict:
        self.created = (title, start_time, end_time)
        return {
            "id": 1,
            "title": title,
            "start_time": start_time,
            "end_time": end_time,
        }

    async def get_appointment(self, appointment_id: int) -> dict | None:
        return None

    async def get_appointments(self) -> list[dict]:
        return []

    async def update_appointment(
        self, appointment_id: int, title: str, start_time: datetime, end_time: datetime
    ) -> dict | None:
        return None

    async def delete_appointment(self, appointment_id: int) -> None:
        return None


def test_create_appointment_normalizes_title() -> None:
    gateway = StubAppointmentGateway()
    controller = AppointmentController(gateway)
    start_time = datetime(2026, 3, 21, 9, 0, 0)
    end_time = datetime(2026, 3, 21, 10, 0, 0)

    appointment = asyncio.run(
        controller.create_appointment("  Weekly sync  ", start_time, end_time)
    )

    assert gateway.conflict_checks == [(start_time, end_time, None)]
    assert gateway.created == ("Weekly sync", start_time, end_time)
    assert appointment == {
        "id": 1,
        "title": "Weekly sync",
        "start_time": start_time,
        "end_time": end_time,
    }


def test_create_appointment_rejects_blank_titles() -> None:
    controller = AppointmentController(StubAppointmentGateway())
    start_time = datetime(2026, 3, 21, 9, 0, 0)
    end_time = datetime(2026, 3, 21, 10, 0, 0)

    with pytest.raises(ValueError, match="title must not be empty"):
        asyncio.run(controller.create_appointment("   ", start_time, end_time))


def test_create_appointment_rejects_invalid_ranges() -> None:
    controller = AppointmentController(StubAppointmentGateway())
    start_time = datetime(2026, 3, 21, 10, 0, 0)
    end_time = datetime(2026, 3, 21, 9, 0, 0)

    with pytest.raises(ValueError, match="end_time must be after start_time"):
        asyncio.run(controller.create_appointment("Weekly sync", start_time, end_time))
