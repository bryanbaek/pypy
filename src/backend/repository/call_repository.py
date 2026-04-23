"""Repository for call-hold detector sessions and per-call events."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol


class CallConnection(Protocol):
    """Minimal async database interface used by the call repository."""

    async def execute(self, query: str, *args: object) -> object: ...

    async def fetch(self, query: str, *args: object) -> list[dict]: ...

    async def fetchrow(self, query: str, *args: object) -> dict | None: ...


def _row_to_call(row: dict | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row["id"],
        "support_number": row["support_number"],
        "user_callback_number": row["user_callback_number"],
        "state": row["state"],
        "twilio_call_sid": row.get("twilio_call_sid"),
        "notified_at": row.get("notified_at"),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _row_to_event(row: dict | None) -> dict | None:
    if row is None:
        return None
    return {
        "id": row["id"],
        "call_id": row["call_id"],
        "event_type": row["event_type"],
        "state": row.get("state"),
        "payload": row.get("payload"),
        "created_at": row["created_at"],
    }


async def create_call(
    conn: CallConnection,
    *,
    session_id: str,
    support_number: str,
    user_callback_number: str,
    twilio_call_sid: str | None,
) -> dict:
    """Insert a new call session row."""
    row = await conn.fetchrow(
        """
        INSERT INTO calls (id, support_number, user_callback_number, state, twilio_call_sid)
        VALUES ($1, $2, $3, 'unknown', $4)
        RETURNING id, support_number, user_callback_number, state, twilio_call_sid,
                  notified_at, created_at, updated_at
        """,
        session_id,
        support_number,
        user_callback_number,
        twilio_call_sid,
    )
    call = _row_to_call(row)
    if call is None:
        raise RuntimeError("Failed to persist call session.")
    return call


async def update_call_state(
    conn: CallConnection,
    *,
    session_id: str,
    state: str,
    notified_at: datetime | None = None,
) -> dict | None:
    """Update the coarse state for a session and optionally record notification time."""
    row = await conn.fetchrow(
        """
        UPDATE calls
        SET state = $2,
            notified_at = COALESCE($3, notified_at)
        WHERE id = $1
        RETURNING id, support_number, user_callback_number, state, twilio_call_sid,
                  notified_at, created_at, updated_at
        """,
        session_id,
        state,
        notified_at,
    )
    return _row_to_call(row)


async def get_call(conn: CallConnection, session_id: str) -> dict | None:
    row = await conn.fetchrow(
        """
        SELECT id, support_number, user_callback_number, state, twilio_call_sid,
               notified_at, created_at, updated_at
        FROM calls
        WHERE id = $1
        """,
        session_id,
    )
    return _row_to_call(row)


async def append_call_event(
    conn: CallConnection,
    *,
    session_id: str,
    event_type: str,
    state: str | None = None,
    payload: object | None = None,
) -> dict:
    """Record a per-frame or state-transition event for the session."""
    row = await conn.fetchrow(
        """
        INSERT INTO call_events (call_id, event_type, state, payload)
        VALUES ($1, $2, $3, $4)
        RETURNING id, call_id, event_type, state, payload, created_at
        """,
        session_id,
        event_type,
        state,
        payload,
    )
    event = _row_to_event(row)
    if event is None:
        raise RuntimeError("Failed to persist call event.")
    return event


async def list_call_events(
    conn: CallConnection,
    session_id: str,
    *,
    limit: int = 200,
) -> list[dict]:
    rows = await conn.fetch(
        """
        SELECT id, call_id, event_type, state, payload, created_at
        FROM call_events
        WHERE call_id = $1
        ORDER BY created_at ASC
        LIMIT $2
        """,
        session_id,
        limit,
    )
    events: list[dict] = []
    for row in rows:
        event = _row_to_event(row)
        if event is not None:
            events.append(event)
    return events


__all__ = [
    "CallConnection",
    "append_call_event",
    "create_call",
    "get_call",
    "list_call_events",
    "update_call_state",
]
