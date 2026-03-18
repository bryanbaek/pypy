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
