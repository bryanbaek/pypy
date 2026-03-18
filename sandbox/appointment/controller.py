from datetime import datetime

from src.backend.core import validate_appointment_window


class AppointmentController:
    def __init__(self, gateway):
        self._gateway = gateway

    async def create_appointment(
        self, title: str, start_time: datetime, end_time: datetime
    ) -> dict:
        window = validate_appointment_window(title, start_time, end_time)

        if await self._gateway.has_conflict(window.start_time, window.end_time):
            raise ValueError("appointment conflicts with an existing booking")

        return await self._gateway.create_appointment(
            window.title,
            window.start_time,
            window.end_time,
        )

    async def get_appointment(self, appointment_id: int) -> dict | None:
        return await self._gateway.get_appointment(appointment_id)

    async def get_appointments(self) -> list[dict]:
        return await self._gateway.get_appointments()

    async def update_appointment(
        self,
        appointment_id: int,
        title: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict:
        existing = await self._gateway.get_appointment(appointment_id)
        if existing is None:
            raise ValueError("appointment not found")

        window = validate_appointment_window(
            title=existing["title"] if title is None else title,
            start_time=existing["start_time"] if start_time is None else start_time,
            end_time=existing["end_time"] if end_time is None else end_time,
        )

        if await self._gateway.has_conflict(
            window.start_time,
            window.end_time,
            exclude_appointment_id=appointment_id,
        ):
            raise ValueError("appointment conflicts with an existing booking")

        appointment = await self._gateway.update_appointment(
            appointment_id,
            window.title,
            window.start_time,
            window.end_time,
        )
        if appointment is None:
            raise ValueError("appointment not found")
        return appointment

    async def delete_appointment(self, appointment_id: int) -> dict:
        existing = await self._gateway.get_appointment(appointment_id)
        if existing is None:
            raise ValueError("appointment not found")

        await self._gateway.delete_appointment(appointment_id)
        return {"deleted_id": appointment_id}
