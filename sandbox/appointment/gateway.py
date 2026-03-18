from datetime import datetime

from . import repository as default_repository


class AppointmentGateway:
    def __init__(self, conn, repository=default_repository):
        self._conn = conn
        self._repository = repository

    async def has_conflict(
        self,
        start_time: datetime,
        end_time: datetime,
        exclude_appointment_id: int | None = None,
    ) -> bool:
        return await self._repository.has_conflict(
            self._conn,
            start_time,
            end_time,
            exclude_appointment_id=exclude_appointment_id,
        )

    async def create_appointment(
        self, title: str, start_time: datetime, end_time: datetime
    ) -> dict:
        return await self._repository.create_appointment(
            self._conn, title, start_time, end_time
        )

    async def get_appointment(self, appointment_id: int) -> dict | None:
        return await self._repository.get_appointment(self._conn, appointment_id)

    async def get_appointments(self) -> list[dict]:
        return await self._repository.get_appointments(self._conn)

    async def update_appointment(
        self,
        appointment_id: int,
        title: str,
        start_time: datetime,
        end_time: datetime,
    ) -> dict | None:
        return await self._repository.update_appointment(
            self._conn, appointment_id, title, start_time, end_time
        )

    async def delete_appointment(self, appointment_id: int) -> None:
        await self._repository.delete_appointment(self._conn, appointment_id)
