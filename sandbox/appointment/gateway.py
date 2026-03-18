from datetime import datetime

from . import repository as default_repository


class AppointmentGateway:
    def __init__(self, conn, repository=default_repository):
        self._conn = conn
        self._repository = repository

    async def has_conflict(self, start_time: datetime, end_time: datetime) -> bool:
        return await self._repository.has_conflict(self._conn, start_time, end_time)

    async def create_appointment(
        self, title: str, start_time: datetime, end_time: datetime
    ) -> dict:
        return await self._repository.create_appointment(
            self._conn, title, start_time, end_time
        )
