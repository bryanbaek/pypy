import asyncio
from datetime import datetime

import pytest

from sandbox.appointment.controller import AppointmentController
from sandbox.appointment.gateway import AppointmentGateway
from sandbox.appointment.handlers import handle_create_appointment
from sandbox.appointment.repository import create_appointment, has_conflict


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


class FakeRepository:
    def __init__(self, conflict=False):
        self.conflict = conflict
        self.calls = []

    async def has_conflict(self, conn, start_time, end_time):
        self.calls.append(("has_conflict", conn, start_time, end_time))
        return self.conflict

    async def create_appointment(self, conn, title, start_time, end_time):
        self.calls.append(("create_appointment", conn, title, start_time, end_time))
        return {"title": title, "start_time": start_time, "end_time": end_time}


class FakeGateway:
    def __init__(self, conflict=False):
        self.conflict = conflict
        self.calls = []

    async def has_conflict(self, start_time, end_time):
        self.calls.append(("has_conflict", start_time, end_time))
        return self.conflict

    async def create_appointment(self, title, start_time, end_time):
        self.calls.append(("create_appointment", title, start_time, end_time))
        return {"title": title, "start_time": start_time, "end_time": end_time}


def test_repository_has_conflict_returns_true_when_overlapping_window_exists():
    existing_start = datetime(2026, 1, 10, 10, 30, 0)
    existing_end = datetime(2026, 1, 10, 11, 30, 0)
    conn = FakeConn(existing=[(existing_start, existing_end)])

    start_time = datetime(2026, 1, 10, 10, 0, 0)
    end_time = datetime(2026, 1, 10, 11, 0, 0)

    result = asyncio.run(has_conflict(conn, start_time, end_time))

    assert result is True
    assert len(conn.calls) == 1
    assert "FROM appointments" in conn.calls[0][0]


def test_repository_create_appointment_persists_and_returns_payload():
    conn = FakeConn()
    start_time = datetime(2026, 1, 10, 12, 0, 0)
    end_time = datetime(2026, 1, 10, 13, 0, 0)

    result = asyncio.run(create_appointment(conn, "Consultation", start_time, end_time))

    assert result == {
        "title": "Consultation",
        "start_time": start_time,
        "end_time": end_time,
    }
    assert conn.calls == [
        (
            "INSERT INTO appointments (title, start_time, end_time) VALUES ($1, $2, $3)",
            ("Consultation", start_time, end_time),
        )
    ]


def test_gateway_delegates_to_repository_with_connection_context():
    conn = object()
    repository = FakeRepository(conflict=False)
    gateway = AppointmentGateway(conn, repository=repository)
    start_time = datetime(2026, 1, 10, 10, 0, 0)
    end_time = datetime(2026, 1, 10, 11, 0, 0)

    conflict = asyncio.run(gateway.has_conflict(start_time, end_time))
    created = asyncio.run(gateway.create_appointment("Title", start_time, end_time))

    assert conflict is False
    assert created["title"] == "Title"
    assert repository.calls == [
        ("has_conflict", conn, start_time, end_time),
        ("create_appointment", conn, "Title", start_time, end_time),
    ]


def test_controller_applies_core_validation_and_normalizes_title():
    gateway = FakeGateway(conflict=False)
    controller = AppointmentController(gateway)
    start_time = datetime(2026, 1, 10, 9, 0, 0)
    end_time = datetime(2026, 1, 10, 10, 0, 0)

    result = asyncio.run(
        controller.create_appointment("  Intake   Session  ", start_time, end_time)
    )

    assert result["title"] == "Intake Session"
    assert gateway.calls == [
        ("has_conflict", start_time, end_time),
        ("create_appointment", "Intake Session", start_time, end_time),
    ]


def test_controller_rejects_conflicting_appointment_window():
    gateway = FakeGateway(conflict=True)
    controller = AppointmentController(gateway)
    start_time = datetime(2026, 1, 10, 10, 0, 0)
    end_time = datetime(2026, 1, 10, 11, 0, 0)

    with pytest.raises(
        ValueError, match="appointment conflicts with an existing booking"
    ):
        asyncio.run(controller.create_appointment("Haircut", start_time, end_time))

    assert gateway.calls == [("has_conflict", start_time, end_time)]


def test_controller_rejects_outside_business_hours_before_gateway_call():
    gateway = FakeGateway(conflict=False)
    controller = AppointmentController(gateway)
    start_time = datetime(2026, 1, 10, 8, 59, 0)
    end_time = datetime(2026, 1, 10, 9, 30, 0)

    with pytest.raises(
        ValueError, match="appointment must be within business hours \\(09:00-17:00\\)"
    ):
        asyncio.run(controller.create_appointment("Haircut", start_time, end_time))

    assert gateway.calls == []


def test_handler_returns_error_for_invalid_payload():
    gateway = FakeGateway(conflict=False)
    controller = AppointmentController(gateway)

    result = asyncio.run(
        handle_create_appointment(
            controller,
            {
                "title": "Haircut",
                "start_time": "not-a-datetime",
                "end_time": "2026-01-10T11:00:00",
            },
        )
    )

    assert result["status"] == "error"
    assert "Invalid isoformat string" in result["error"]


def test_handler_controller_gateway_repository_integration_happy_path():
    conn = FakeConn()
    gateway = AppointmentGateway(conn)
    controller = AppointmentController(gateway)

    result = asyncio.run(
        handle_create_appointment(
            controller,
            {
                "title": "  New   Client  Intake ",
                "start_time": "2026-01-10T10:00:00",
                "end_time": "2026-01-10T11:00:00",
            },
        )
    )

    assert result["status"] == "ok"
    assert result["appointment"]["title"] == "New Client Intake"
    assert len(conn.calls) == 2
    assert "FROM appointments" in conn.calls[0][0]
    assert conn.calls[1][1] == (
        "New Client Intake",
        datetime(2026, 1, 10, 10, 0, 0),
        datetime(2026, 1, 10, 11, 0, 0),
    )
