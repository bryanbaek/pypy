import asyncio
from datetime import datetime
from pathlib import Path

import pytest

from sandbox.appointment import handlers as appointment_handlers
from sandbox.appointment.controller import AppointmentController
from sandbox.appointment.gateway import AppointmentGateway
from sandbox.appointment.handlers import (
    handle_create_appointment,
    handle_delete_appointment,
    handle_get_appointment,
    handle_get_appointments,
    handle_update_appointment,
)
from sandbox.appointment.repository import (
    create_appointment,
    delete_appointment,
    get_appointment,
    get_appointments,
    has_conflict,
    update_appointment,
)


class FakeConn:
    def __init__(self, existing=None):
        self.calls = []
        self.appointments = []
        self._next_id = 1

        for existing_start, existing_end in existing or []:
            self.appointments.append(
                {
                    "id": self._next_id,
                    "title": f"Existing {self._next_id}",
                    "start_time": existing_start,
                    "end_time": existing_end,
                }
            )
            self._next_id += 1

    async def execute(self, query, *args):
        self.calls.append((query, args))
        if "DELETE FROM appointments" in query:
            appointment_id = args[0]
            self.appointments = [
                appointment
                for appointment in self.appointments
                if appointment["id"] != appointment_id
            ]

    async def fetch(self, query, *args):
        self.calls.append((query, args))

        if "SELECT 1" in query and "FROM appointments" in query:
            start_time, end_time = args[0], args[1]
            exclude_appointment_id = args[2] if len(args) > 2 else None
            for appointment in self.appointments:
                if (
                    exclude_appointment_id is not None
                    and appointment["id"] == exclude_appointment_id
                ):
                    continue
                if (
                    appointment["start_time"] < end_time
                    and appointment["end_time"] > start_time
                ):
                    return [1]
            return []

        if "SELECT id, title, start_time, end_time" in query and "ORDER BY" in query:
            return sorted(
                self.appointments, key=lambda appointment: appointment["start_time"]
            )

        return []

    async def fetchrow(self, query, *args):
        self.calls.append((query, args))

        if "INSERT INTO appointments" in query and "RETURNING" in query:
            appointment = {
                "id": self._next_id,
                "title": args[0],
                "start_time": args[1],
                "end_time": args[2],
            }
            self._next_id += 1
            self.appointments.append(appointment)
            return appointment

        if (
            "SELECT id, title, start_time, end_time" in query
            and "WHERE id = $1" in query
        ):
            appointment_id = args[0]
            for appointment in self.appointments:
                if appointment["id"] == appointment_id:
                    return appointment
            return None

        if "UPDATE appointments" in query and "RETURNING" in query:
            appointment_id = args[3]
            for appointment in self.appointments:
                if appointment["id"] == appointment_id:
                    appointment["title"] = args[0]
                    appointment["start_time"] = args[1]
                    appointment["end_time"] = args[2]
                    return appointment
            return None

        return None


class FakeConnNoInsertReturn(FakeConn):
    async def fetchrow(self, query, *args):
        if "INSERT INTO appointments" in query and "RETURNING" in query:
            self.calls.append((query, args))
            return None
        return await super().fetchrow(query, *args)


class FakeRepository:
    def __init__(self, conflict=False):
        self.conflict = conflict
        self.calls = []

    async def has_conflict(
        self, conn, start_time, end_time, exclude_appointment_id=None
    ):
        self.calls.append(
            (
                "has_conflict",
                conn,
                start_time,
                end_time,
                exclude_appointment_id,
            )
        )
        return self.conflict

    async def create_appointment(self, conn, title, start_time, end_time):
        self.calls.append(("create_appointment", conn, title, start_time, end_time))
        return {
            "id": 1,
            "title": title,
            "start_time": start_time,
            "end_time": end_time,
        }

    async def get_appointment(self, conn, appointment_id):
        self.calls.append(("get_appointment", conn, appointment_id))
        return {
            "id": appointment_id,
            "title": "Title",
            "start_time": datetime(2026, 1, 10, 10, 0, 0),
            "end_time": datetime(2026, 1, 10, 11, 0, 0),
        }

    async def get_appointments(self, conn):
        self.calls.append(("get_appointments", conn))
        return []

    async def update_appointment(
        self, conn, appointment_id, title, start_time, end_time
    ):
        self.calls.append(
            (
                "update_appointment",
                conn,
                appointment_id,
                title,
                start_time,
                end_time,
            )
        )
        return {
            "id": appointment_id,
            "title": title,
            "start_time": start_time,
            "end_time": end_time,
        }

    async def delete_appointment(self, conn, appointment_id):
        self.calls.append(("delete_appointment", conn, appointment_id))


class FakeGateway:
    def __init__(self, conflict=False):
        self.conflict = conflict
        self.calls = []
        self.appointments = {
            1: {
                "id": 1,
                "title": "Initial",
                "start_time": datetime(2026, 1, 10, 10, 0, 0),
                "end_time": datetime(2026, 1, 10, 11, 0, 0),
            }
        }

    async def has_conflict(self, start_time, end_time, exclude_appointment_id=None):
        self.calls.append(
            ("has_conflict", start_time, end_time, exclude_appointment_id)
        )
        return self.conflict

    async def create_appointment(self, title, start_time, end_time):
        self.calls.append(("create_appointment", title, start_time, end_time))
        return {
            "id": 2,
            "title": title,
            "start_time": start_time,
            "end_time": end_time,
        }

    async def get_appointment(self, appointment_id):
        self.calls.append(("get_appointment", appointment_id))
        return self.appointments.get(appointment_id)

    async def get_appointments(self):
        self.calls.append(("get_appointments",))
        return list(self.appointments.values())

    async def update_appointment(self, appointment_id, title, start_time, end_time):
        self.calls.append(
            ("update_appointment", appointment_id, title, start_time, end_time)
        )
        appointment = self.appointments.get(appointment_id)
        if appointment is None:
            return None
        appointment["title"] = title
        appointment["start_time"] = start_time
        appointment["end_time"] = end_time
        return appointment

    async def delete_appointment(self, appointment_id):
        self.calls.append(("delete_appointment", appointment_id))
        self.appointments.pop(appointment_id, None)


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


def test_repository_has_conflict_supports_excluding_same_appointment():
    existing_start = datetime(2026, 1, 10, 10, 30, 0)
    existing_end = datetime(2026, 1, 10, 11, 30, 0)
    conn = FakeConn(existing=[(existing_start, existing_end)])

    start_time = datetime(2026, 1, 10, 10, 0, 0)
    end_time = datetime(2026, 1, 10, 11, 0, 0)

    excluded_result = asyncio.run(has_conflict(conn, start_time, end_time, 1))
    non_excluded_result = asyncio.run(has_conflict(conn, start_time, end_time))

    assert excluded_result is False
    assert non_excluded_result is True


def test_repository_crud_roundtrip():
    conn = FakeConn()
    start_time = datetime(2026, 1, 10, 12, 0, 0)
    end_time = datetime(2026, 1, 10, 13, 0, 0)

    created = asyncio.run(
        create_appointment(conn, "Consultation", start_time, end_time)
    )
    fetched = asyncio.run(get_appointment(conn, created["id"]))
    listing = asyncio.run(get_appointments(conn))

    assert created["id"] == 1
    assert fetched == created
    assert listing == [created]

    updated = asyncio.run(
        update_appointment(
            conn,
            created["id"],
            "Follow Up",
            start_time,
            datetime(2026, 1, 10, 14, 0, 0),
        )
    )
    assert updated is not None
    assert updated["title"] == "Follow Up"

    asyncio.run(delete_appointment(conn, created["id"]))
    assert asyncio.run(get_appointment(conn, created["id"])) is None


def test_repository_create_returns_fallback_payload_when_row_missing():
    conn = FakeConnNoInsertReturn()
    start_time = datetime(2026, 1, 10, 12, 0, 0)
    end_time = datetime(2026, 1, 10, 13, 0, 0)

    created = asyncio.run(
        create_appointment(conn, "Consultation", start_time, end_time)
    )

    assert created == {
        "title": "Consultation",
        "start_time": start_time,
        "end_time": end_time,
    }


def test_gateway_delegates_to_repository_with_connection_context():
    conn = object()
    repository = FakeRepository(conflict=False)
    gateway = AppointmentGateway(conn, repository=repository)
    start_time = datetime(2026, 1, 10, 10, 0, 0)
    end_time = datetime(2026, 1, 10, 11, 0, 0)

    conflict = asyncio.run(gateway.has_conflict(start_time, end_time))
    created = asyncio.run(gateway.create_appointment("Title", start_time, end_time))
    fetched = asyncio.run(gateway.get_appointment(3))
    listing = asyncio.run(gateway.get_appointments())
    asyncio.run(gateway.update_appointment(3, "Updated", start_time, end_time))
    asyncio.run(gateway.delete_appointment(3))

    assert conflict is False
    assert created["title"] == "Title"
    assert fetched is not None
    assert listing == []
    assert repository.calls == [
        ("has_conflict", conn, start_time, end_time, None),
        ("create_appointment", conn, "Title", start_time, end_time),
        ("get_appointment", conn, 3),
        ("get_appointments", conn),
        ("update_appointment", conn, 3, "Updated", start_time, end_time),
        ("delete_appointment", conn, 3),
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
        ("has_conflict", start_time, end_time, None),
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

    assert gateway.calls == [("has_conflict", start_time, end_time, None)]


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


def test_controller_update_validates_and_excludes_same_appointment_for_conflict_check():
    gateway = FakeGateway(conflict=False)
    controller = AppointmentController(gateway)

    result = asyncio.run(
        controller.update_appointment(
            1,
            title="  Updated   Session  ",
            start_time=datetime(2026, 1, 10, 10, 30, 0),
            end_time=datetime(2026, 1, 10, 11, 30, 0),
        )
    )

    assert result["title"] == "Updated Session"
    assert gateway.calls == [
        ("get_appointment", 1),
        (
            "has_conflict",
            datetime(2026, 1, 10, 10, 30, 0),
            datetime(2026, 1, 10, 11, 30, 0),
            1,
        ),
        (
            "update_appointment",
            1,
            "Updated Session",
            datetime(2026, 1, 10, 10, 30, 0),
            datetime(2026, 1, 10, 11, 30, 0),
        ),
    ]


def test_controller_update_rejects_conflicting_appointment_window():
    gateway = FakeGateway(conflict=True)
    controller = AppointmentController(gateway)

    with pytest.raises(
        ValueError, match="appointment conflicts with an existing booking"
    ):
        asyncio.run(
            controller.update_appointment(
                1,
                start_time=datetime(2026, 1, 10, 10, 30, 0),
                end_time=datetime(2026, 1, 10, 11, 30, 0),
            )
        )

    assert gateway.calls == [
        ("get_appointment", 1),
        (
            "has_conflict",
            datetime(2026, 1, 10, 10, 30, 0),
            datetime(2026, 1, 10, 11, 30, 0),
            1,
        ),
    ]


def test_controller_update_rejects_missing_appointment():
    gateway = FakeGateway(conflict=False)
    gateway.appointments = {}
    controller = AppointmentController(gateway)

    with pytest.raises(ValueError, match="appointment not found"):
        asyncio.run(controller.update_appointment(1, title="Updated"))

    assert gateway.calls == [("get_appointment", 1)]


def test_controller_delete_rejects_missing_appointment():
    gateway = FakeGateway(conflict=False)
    gateway.appointments = {}
    controller = AppointmentController(gateway)

    with pytest.raises(ValueError, match="appointment not found"):
        asyncio.run(controller.delete_appointment(1))

    assert gateway.calls == [("get_appointment", 1)]


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


def test_handler_returns_error_for_missing_required_create_field():
    gateway = FakeGateway(conflict=False)
    controller = AppointmentController(gateway)

    result = asyncio.run(
        handle_create_appointment(
            controller,
            {
                "title": "Haircut",
                "start_time": "2026-01-10T10:00:00",
            },
        )
    )

    assert result["status"] == "error"
    assert result["error"] == "'end_time'"


def test_handler_returns_error_for_non_string_title():
    gateway = FakeGateway(conflict=False)
    controller = AppointmentController(gateway)

    result = asyncio.run(
        handle_create_appointment(
            controller,
            {
                "title": 123,
                "start_time": "2026-01-10T10:00:00",
                "end_time": "2026-01-10T11:00:00",
            },
        )
    )

    assert result["status"] == "error"
    assert result["error"] == "title must be a string"


def test_handler_update_returns_error_for_invalid_payload():
    gateway = FakeGateway(conflict=False)
    controller = AppointmentController(gateway)

    result = asyncio.run(
        handle_update_appointment(
            controller,
            1,
            {
                "start_time": "not-a-datetime",
            },
        )
    )

    assert result["status"] == "error"
    assert "Invalid isoformat string" in result["error"]


def test_handler_delete_returns_error_when_missing_appointment():
    gateway = FakeGateway(conflict=False)
    gateway.appointments = {}
    controller = AppointmentController(gateway)

    result = asyncio.run(handle_delete_appointment(controller, 1))

    assert result == {"status": "error", "error": "appointment not found"}


def test_handler_controller_gateway_repository_integration_happy_path():
    conn = FakeConn()
    gateway = AppointmentGateway(conn)
    controller = AppointmentController(gateway)

    created = asyncio.run(
        handle_create_appointment(
            controller,
            {
                "title": "  New   Client  Intake ",
                "start_time": "2026-01-10T10:00:00",
                "end_time": "2026-01-10T11:00:00",
            },
        )
    )

    assert created["status"] == "ok"
    appointment_id = created["appointment"]["id"]
    assert created["appointment"]["title"] == "New Client Intake"

    fetched = asyncio.run(handle_get_appointment(controller, appointment_id))
    assert fetched["status"] == "ok"
    assert fetched["appointment"]["id"] == appointment_id

    listing = asyncio.run(handle_get_appointments(controller))
    assert listing["status"] == "ok"
    assert len(listing["appointments"]) == 1

    updated = asyncio.run(
        handle_update_appointment(
            controller,
            appointment_id,
            {
                "title": "  Updated   Intake  ",
                "start_time": "2026-01-10T10:15:00",
                "end_time": "2026-01-10T11:15:00",
            },
        )
    )
    assert updated["status"] == "ok"
    assert updated["appointment"]["title"] == "Updated Intake"

    deleted = asyncio.run(handle_delete_appointment(controller, appointment_id))
    assert deleted == {"status": "ok", "deleted_id": appointment_id}

    missing = asyncio.run(handle_get_appointment(controller, appointment_id))
    assert missing == {"status": "error", "error": "appointment not found"}


def test_handler_controller_gateway_repository_rejects_overlapping_window():
    conn = FakeConn()
    gateway = AppointmentGateway(conn)
    controller = AppointmentController(gateway)

    first = asyncio.run(
        handle_create_appointment(
            controller,
            {
                "title": "Initial Session",
                "start_time": "2026-01-10T10:00:00",
                "end_time": "2026-01-10T11:00:00",
            },
        )
    )
    assert first["status"] == "ok"

    overlapping = asyncio.run(
        handle_create_appointment(
            controller,
            {
                "title": "Overlapping Session",
                "start_time": "2026-01-10T10:30:00",
                "end_time": "2026-01-10T11:30:00",
            },
        )
    )

    assert overlapping == {
        "status": "error",
        "error": "appointment conflicts with an existing booking",
    }


def test_handler_happy_path_writes_core_mvp_verification_artifact(tmp_path, monkeypatch):
    artifact_path = tmp_path / "core-mvp-20260319T195344Z-happy.md"
    monkeypatch.setattr(
        appointment_handlers, "HAPPY_PATH_ARTIFACT_PATH", artifact_path
    )

    gateway = FakeGateway(conflict=False)
    controller = AppointmentController(gateway)

    created = asyncio.run(
        handle_create_appointment(
            controller,
            {
                "title": "New Client Intake",
                "start_time": "2026-01-10T10:00:00",
                "end_time": "2026-01-10T11:00:00",
            },
        )
    )

    assert created["status"] == "ok"
    assert artifact_path.exists()
    artifact_content = artifact_path.read_text(encoding="utf-8")
    assert "tag: core-mvp-20260319T195344Z-happy" in artifact_content
    assert "scenario: happy" in artifact_content


def test_happy_path_marker_artifact_exists_with_expected_tag_and_scenario():
    artifact_path = appointment_handlers.HAPPY_PATH_ARTIFACT_PATH

    assert artifact_path.exists()
    artifact_content = artifact_path.read_text(encoding="utf-8")
    assert f"tag: {appointment_handlers.HAPPY_PATH_ARTIFACT_TAG}" in artifact_content
    assert (
        f"scenario: {appointment_handlers.HAPPY_PATH_ARTIFACT_SCENARIO}"
        in artifact_content
    )


def test_run_specific_happy_path_marker_artifact_exists_with_expected_tag_and_scenario():
    artifact_path = (
        Path(__file__).resolve().parents[1]
        / "sandbox"
        / "appointment"
        / "e2e"
        / "core-mvp-20260319T213245Z-happy.md"
    )

    assert artifact_path.exists()
    artifact_content = artifact_path.read_text(encoding="utf-8")
    assert "tag: core-mvp-20260319T213245Z-happy" in artifact_content
    assert "scenario: happy" in artifact_content
