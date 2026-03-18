"""Gateway layer for sandbox appointment workflows."""

from datetime import datetime
from typing import Protocol

from . import repository as default_repository
from .repository import AppointmentConnection


class AppointmentRepository(Protocol):
    """Repository contract used by the appointment gateway."""

    async def has_conflict(
        self,
        conn: AppointmentConnection,
        start_time: datetime,
        end_time: datetime,
        exclude_appointment_id: int | None = None,
    ) -> bool: ...

    async def create_appointment(
        self,
        conn: AppointmentConnection,
        title: str,
        start_time: datetime,
        end_time: datetime,
    ) -> dict: ...

    async def get_appointment(
        self, conn: AppointmentConnection, appointment_id: int
    ) -> dict | None: ...

    async def get_appointments(self, conn: AppointmentConnection) -> list[dict]: ...

    async def update_appointment(
        self,
        conn: AppointmentConnection,
        appointment_id: int,
        title: str,
        start_time: datetime,
        end_time: datetime,
    ) -> dict | None: ...

    async def delete_appointment(
        self, conn: AppointmentConnection, appointment_id: int
    ) -> None: ...


class AppointmentGateway:
    """Abstraction over repository access for appointment operations."""

    def __init__(
        self,
        conn: AppointmentConnection,
        repository: AppointmentRepository = default_repository,
    ) -> None:
        self._conn = conn
        self._repository = repository

    async def has_conflict(
        self,
        start_time: datetime,
        end_time: datetime,
        exclude_appointment_id: int | None = None,
    ) -> bool:
        """Check whether a requested appointment window conflicts."""
        return await self._repository.has_conflict(
            self._conn,
            start_time,
            end_time,
            exclude_appointment_id=exclude_appointment_id,
        )

    async def create_appointment(
        self, title: str, start_time: datetime, end_time: datetime
    ) -> dict:
        """Create an appointment through the repository."""
        return await self._repository.create_appointment(
            self._conn, title, start_time, end_time
        )

    async def get_appointment(self, appointment_id: int) -> dict | None:
        """Get a single appointment by id."""
        return await self._repository.get_appointment(self._conn, appointment_id)

    async def get_appointments(self) -> list[dict]:
        """List all appointments."""
        return await self._repository.get_appointments(self._conn)

    async def update_appointment(
        self,
        appointment_id: int,
        title: str,
        start_time: datetime,
        end_time: datetime,
    ) -> dict | None:
        """Update an existing appointment by id."""
        return await self._repository.update_appointment(
            self._conn, appointment_id, title, start_time, end_time
        )

    async def delete_appointment(self, appointment_id: int) -> None:
        """Delete an appointment by id."""
        await self._repository.delete_appointment(self._conn, appointment_id)
