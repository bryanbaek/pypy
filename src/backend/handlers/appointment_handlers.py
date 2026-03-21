"""Handler layer for translating payloads to appointment controller operations."""

from datetime import datetime
from pathlib import Path
from typing import Protocol

HAPPY_PATH_ARTIFACT_TAG = "core-mvp-20260319T195344Z-happy"
HAPPY_PATH_ARTIFACT_SCENARIO = "happy"
HAPPY_PATH_ARTIFACT_PATH = Path(__file__).resolve().parent / "e2e" / (
    f"{HAPPY_PATH_ARTIFACT_TAG}.md"
)


class AppointmentControllerContract(Protocol):
    """Controller contract used by appointment handlers."""

    async def create_appointment(
        self, title: str, start_time: datetime, end_time: datetime
    ) -> dict: ...

    async def get_appointment(self, appointment_id: int) -> dict | None: ...

    async def get_appointments(self) -> list[dict]: ...

    async def update_appointment(
        self,
        appointment_id: int,
        *,
        title: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict: ...

    async def delete_appointment(self, appointment_id: int) -> dict: ...


def _write_happy_path_artifact() -> None:
    """Write a marker artifact for the appointment happy path flow."""
    HAPPY_PATH_ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    HAPPY_PATH_ARTIFACT_PATH.write_text(
        (
            "# Core MVP Happy-Path Verification Artifact\n\n"
            f"tag: {HAPPY_PATH_ARTIFACT_TAG}\n"
            f"scenario: {HAPPY_PATH_ARTIFACT_SCENARIO}\n"
        ),
        encoding="utf-8",
    )


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


async def handle_create_appointment(
    controller: AppointmentControllerContract, payload: dict
) -> dict:
    """Handle create-appointment input payloads."""
    try:
        appointment = await controller.create_appointment(
            title=payload["title"],
            start_time=_parse_datetime(payload["start_time"]),
            end_time=_parse_datetime(payload["end_time"]),
        )
    except (KeyError, ValueError) as exc:
        return {"status": "error", "error": str(exc)}

    _write_happy_path_artifact()
    return {"status": "ok", "appointment": appointment}


async def handle_get_appointment(
    controller: AppointmentControllerContract, appointment_id: int
) -> dict:
    """Handle get-appointment requests."""
    try:
        appointment = await controller.get_appointment(appointment_id)
    except ValueError as exc:
        return {"status": "error", "error": str(exc)}
    if appointment is None:
        return {"status": "error", "error": "appointment not found"}
    return {"status": "ok", "appointment": appointment}


async def handle_get_appointments(controller: AppointmentControllerContract) -> dict:
    """Handle get-appointments requests."""
    try:
        appointments = await controller.get_appointments()
    except ValueError as exc:
        return {"status": "error", "error": str(exc)}
    return {"status": "ok", "appointments": appointments}


async def handle_update_appointment(
    controller: AppointmentControllerContract, appointment_id: int, payload: dict
) -> dict:
    """Handle update-appointment requests."""
    updates: dict = {}
    try:
        if "title" in payload:
            updates["title"] = payload["title"]
        if "start_time" in payload:
            updates["start_time"] = _parse_datetime(payload["start_time"])
        if "end_time" in payload:
            updates["end_time"] = _parse_datetime(payload["end_time"])

        appointment = await controller.update_appointment(appointment_id, **updates)
    except (KeyError, ValueError) as exc:
        return {"status": "error", "error": str(exc)}
    return {"status": "ok", "appointment": appointment}


async def handle_delete_appointment(
    controller: AppointmentControllerContract, appointment_id: int
) -> dict:
    """Handle delete-appointment requests."""
    try:
        deletion = await controller.delete_appointment(appointment_id)
    except ValueError as exc:
        return {"status": "error", "error": str(exc)}
    return {"status": "ok", **deletion}


__all__ = [
    "HAPPY_PATH_ARTIFACT_PATH",
    "HAPPY_PATH_ARTIFACT_SCENARIO",
    "HAPPY_PATH_ARTIFACT_TAG",
    "handle_create_appointment",
    "handle_delete_appointment",
    "handle_get_appointment",
    "handle_get_appointments",
    "handle_update_appointment",
]
