"""Tests for the call repository helpers."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from src.backend.repository.call_repository import (
    append_call_event,
    create_call,
    get_call,
    list_call_events,
    update_call_state,
)


class _StubCallConnection:
    def __init__(self) -> None:
        self.execute_calls: list[tuple[str, tuple[object, ...]]] = []
        self.fetch_calls: list[tuple[str, tuple[object, ...]]] = []
        self.fetchrow_calls: list[tuple[str, tuple[object, ...]]] = []
        self.fetch_result: list[dict] = []
        self.fetchrow_result: dict | None = None

    async def execute(self, query: str, *args: object) -> object:
        self.execute_calls.append((query, args))
        return "OK"

    async def fetch(self, query: str, *args: object) -> list[dict]:
        self.fetch_calls.append((query, args))
        return self.fetch_result

    async def fetchrow(self, query: str, *args: object) -> dict | None:
        self.fetchrow_calls.append((query, args))
        return self.fetchrow_result


def test_create_call_inserts_row_with_defaults() -> None:
    conn = _StubCallConnection()
    now = datetime.now(tz=timezone.utc)
    conn.fetchrow_result = {
        "id": "abc",
        "support_number": "+18005551212",
        "user_callback_number": "+15555550111",
        "state": "unknown",
        "twilio_call_sid": "CA-1",
        "notified_at": None,
        "created_at": now,
        "updated_at": now,
    }
    call = asyncio.run(
        create_call(
            conn,
            session_id="abc",
            support_number="+18005551212",
            user_callback_number="+15555550111",
            twilio_call_sid="CA-1",
        )
    )
    assert call["id"] == "abc"
    assert call["state"] == "unknown"
    query, args = conn.fetchrow_calls[0]
    assert "INSERT INTO calls" in query
    assert args == ("abc", "+18005551212", "+15555550111", "CA-1")


def test_update_call_state_issues_update_with_coalesced_notified_at() -> None:
    conn = _StubCallConnection()
    now = datetime.now(tz=timezone.utc)
    conn.fetchrow_result = {
        "id": "abc",
        "support_number": "+18005551212",
        "user_callback_number": "+15555550111",
        "state": "human_detected",
        "twilio_call_sid": "CA-1",
        "notified_at": now,
        "created_at": now,
        "updated_at": now,
    }
    result = asyncio.run(
        update_call_state(
            conn,
            session_id="abc",
            state="human_detected",
            notified_at=now,
        )
    )
    assert result is not None
    assert result["state"] == "human_detected"
    query, args = conn.fetchrow_calls[0]
    assert "UPDATE calls" in query
    assert "COALESCE($3, notified_at)" in query
    assert args == ("abc", "human_detected", now)


def test_get_call_returns_none_when_not_found() -> None:
    conn = _StubCallConnection()
    conn.fetchrow_result = None
    result = asyncio.run(get_call(conn, "missing"))
    assert result is None


def test_append_call_event_inserts_event_row() -> None:
    conn = _StubCallConnection()
    now = datetime.now(tz=timezone.utc)
    conn.fetchrow_result = {
        "id": 42,
        "call_id": "abc",
        "event_type": "state_transition",
        "state": "hold_music",
        "payload": {"continuous_speech_seconds": 0.0},
        "created_at": now,
    }
    event = asyncio.run(
        append_call_event(
            conn,
            session_id="abc",
            event_type="state_transition",
            state="hold_music",
            payload={"continuous_speech_seconds": 0.0},
        )
    )
    assert event["event_type"] == "state_transition"
    query, args = conn.fetchrow_calls[0]
    assert "INSERT INTO call_events" in query
    assert args == ("abc", "state_transition", "hold_music", {"continuous_speech_seconds": 0.0})


def test_list_call_events_orders_by_created_at() -> None:
    conn = _StubCallConnection()
    now = datetime.now(tz=timezone.utc)
    conn.fetch_result = [
        {
            "id": 1,
            "call_id": "abc",
            "event_type": "state_transition",
            "state": "hold_music",
            "payload": None,
            "created_at": now,
        },
        {
            "id": 2,
            "call_id": "abc",
            "event_type": "notification",
            "state": "human_detected",
            "payload": None,
            "created_at": now,
        },
    ]
    events = asyncio.run(list_call_events(conn, "abc", limit=50))
    assert len(events) == 2
    query, args = conn.fetch_calls[0]
    assert "ORDER BY created_at ASC" in query
    assert args == ("abc", 50)
