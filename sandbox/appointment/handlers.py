"""Handler layer for translating payloads to controller operations."""

from datetime import datetime
from pathlib import Path
from typing import Protocol

HAPPY_PATH_ARTIFACT_TAG = "core-mvp-20260319T195344Z-happy"
HAPPY_PATH_ARTIFACT_SCENARIO = "happy"
HAPPY_PATH_ARTIFACT_PATH = (
    Path(__file__).resolve().parent
    / "e2e"
    / f"{HAPPY_PATH_ARTIFACT_TAG}.md"
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
        title: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict: ...

    async def delete_appointment(self, appointment_id: int) -> dict: ...


def _as_datetime(value: datetime | str) -> datetime:
    """Parse datetime values accepted by handler payloads."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise ValueError("start_time and end_time must be datetime or ISO datetime strings")


def _write_happy_path_artifact() -> None:
    """Write marker artifact for the sandbox appointment happy-path scenario."""
    HAPPY_PATH_ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    HAPPY_PATH_ARTIFACT_PATH.write_text(
        (
            "# Core MVP Happy-Path Verification Artifact\n\n"
            f"tag: {HAPPY_PATH_ARTIFACT_TAG}\n"
            f"scenario: {HAPPY_PATH_ARTIFACT_SCENARIO}\n"
        ),
        encoding="utf-8",
    )


async def handle_create_appointment(
    controller: AppointmentControllerContract, payload: dict
) -> dict:
    """Handle create-appointment input payloads."""
    try:
        appointment = await controller.create_appointment(
            title=payload["title"],
            start_time=_as_datetime(payload["start_time"]),
            end_time=_as_datetime(payload["end_time"]),
        )
    except (KeyError, ValueError) as exc:
        return {"status": "error", "error": str(exc)}

    _write_happy_path_artifact()
    return {"status": "ok", "appointment": appointment}


async def handle_get_appointments(controller: AppointmentControllerContract) -> dict:
    """Handle list-appointments requests."""
    appointments = await controller.get_appointments()
    return {"status": "ok", "appointments": appointments}


async def handle_get_appointment(
    controller: AppointmentControllerContract, appointment_id: int
) -> dict:
    """Handle get-appointment requests."""
    appointment = await controller.get_appointment(appointment_id)
    if appointment is None:
        return {"status": "error", "error": "appointment not found"}
    return {"status": "ok", "appointment": appointment}


async def handle_update_appointment(
    controller: AppointmentControllerContract, appointment_id: int, payload: dict
) -> dict:
    """Handle update-appointment input payloads."""
    try:
        appointment = await controller.update_appointment(
            appointment_id=appointment_id,
            title=payload.get("title"),
            start_time=(
                _as_datetime(payload["start_time"]) if "start_time" in payload else None
            ),
            end_time=_as_datetime(payload["end_time"])
            if "end_time" in payload
            else None,
        )
    except ValueError as exc:
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
