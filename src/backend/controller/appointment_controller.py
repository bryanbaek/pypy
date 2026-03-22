"""Controller layer coordinating the sample appointment workflow."""

from datetime import datetime
from typing import Protocol


def _prepare_appointment_payload(
    title: str,
    start_time: datetime,
    end_time: datetime,
) -> tuple[str, datetime, datetime]:
    normalized_title = title.strip()
    if not normalized_title:
        raise ValueError("title must not be empty")
    if end_time <= start_time:
        raise ValueError("end_time must be after start_time")
    return normalized_title, start_time, end_time


class AppointmentGatewayContract(Protocol):
    """Gateway contract used by appointment controller orchestration."""

    async def has_conflict(
        self,
        start_time: datetime,
        end_time: datetime,
        exclude_appointment_id: int | None = None,
    ) -> bool: ...

    async def create_appointment(
        self, title: str, start_time: datetime, end_time: datetime
    ) -> dict: ...

    async def get_appointment(self, appointment_id: int) -> dict | None: ...

    async def get_appointments(self) -> list[dict]: ...

    async def update_appointment(
        self, appointment_id: int, title: str, start_time: datetime, end_time: datetime
    ) -> dict | None: ...

    async def delete_appointment(self, appointment_id: int) -> None: ...


class AppointmentController:
    """Application workflow service for the sample appointment flow."""

    def __init__(self, gateway: AppointmentGatewayContract) -> None:
        self._gateway = gateway

    async def create_appointment(
        self, title: str, start_time: datetime, end_time: datetime
    ) -> dict:
        normalized_title, normalized_start_time, normalized_end_time = (
            _prepare_appointment_payload(title, start_time, end_time)
        )
        if await self._gateway.has_conflict(
            normalized_start_time,
            normalized_end_time,
        ):
            raise ValueError("appointment conflicts with an existing booking")
        return await self._gateway.create_appointment(
            normalized_title,
            normalized_start_time,
            normalized_end_time,
        )

    async def get_appointment(self, appointment_id: int) -> dict | None:
        return await self._gateway.get_appointment(appointment_id)

    async def get_appointments(self) -> list[dict]:
        return await self._gateway.get_appointments()

    async def update_appointment(
        self,
        appointment_id: int,
        *,
        title: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict:
        existing = await self._gateway.get_appointment(appointment_id)
        if existing is None:
            raise ValueError("appointment not found")

        normalized_title, normalized_start_time, normalized_end_time = (
            _prepare_appointment_payload(
                existing["title"] if title is None else title,
                existing["start_time"] if start_time is None else start_time,
                existing["end_time"] if end_time is None else end_time,
            )
        )
        if await self._gateway.has_conflict(
            normalized_start_time,
            normalized_end_time,
            exclude_appointment_id=appointment_id,
        ):
            raise ValueError("appointment conflicts with an existing booking")

        updated = await self._gateway.update_appointment(
            appointment_id,
            normalized_title,
            normalized_start_time,
            normalized_end_time,
        )
        if updated is None:
            raise ValueError("appointment not found")
        return updated

    async def delete_appointment(self, appointment_id: int) -> dict:
        existing = await self._gateway.get_appointment(appointment_id)
        if existing is None:
            raise ValueError("appointment not found")

        await self._gateway.delete_appointment(appointment_id)
        return {"deleted_id": appointment_id}


__all__ = ["AppointmentController", "AppointmentGatewayContract"]
