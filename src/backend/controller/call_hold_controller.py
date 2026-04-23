"""Session orchestration for the call-hold detector.

Responsibilities:
  - Allocate a ``CallSession`` when the user asks to dial a support number.
  - Drive the Twilio REST client to place the outbound call.
  - Own per-session audio state (one ``HoldAudioAnalyzer`` per call).
  - Receive decoded PCM frames from the Media Streams websocket handler,
    feed them into the analyzer, and on the first ``HUMAN_DETECTED``
    transition fire the configured ``Notifier`` (SMS + ring-back).

State is kept in-memory, which is fine for MVP (one worker process). For
multi-process deploys this would move to Redis / Postgres.
"""

from __future__ import annotations

import asyncio
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol

import numpy as np

from src.backend.controller.hold_audio_analyzer import (
    AnalyzerConfig,
    CallState,
    HoldAudioAnalyzer,
)


@dataclass
class CallSession:
    """Per-call state shared across the HTTP handlers and the WS handler."""

    id: str
    support_number: str
    user_callback_number: str
    created_at: datetime
    updated_at: datetime
    state: CallState = CallState.UNKNOWN
    twilio_call_sid: str | None = None
    notified_at: datetime | None = None
    analyzer: HoldAudioAnalyzer = field(default_factory=HoldAudioAnalyzer)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)


class Notifier(Protocol):
    """Fire a notification when a human picks up."""

    async def notify_human_detected(self, session: CallSession) -> None: ...


class LoggingNotifier:
    """Default no-op notifier used when Twilio credentials are not configured."""

    def __init__(self) -> None:
        self.events: list[str] = []

    async def notify_human_detected(self, session: CallSession) -> None:
        self.events.append(f"human detected on call {session.id} -> {session.user_callback_number}")


@dataclass(frozen=True)
class DialRequest:
    """Input to ``CallHoldController.start_call``."""

    support_number: str
    user_callback_number: str


@dataclass(frozen=True)
class DialResponse:
    """Returned to the HTTP handler after a dial-out is accepted."""

    session_id: str
    twilio_call_sid: str | None


class CallPlacer(Protocol):
    """Places the Twilio call. Real impl wraps ``TwilioClient``."""

    async def place_call(self, *, session: CallSession) -> str: ...


class CallHoldController:
    """Coordinates call sessions, analyzer input, and notifications."""

    def __init__(
        self,
        *,
        analyzer_config: AnalyzerConfig | None = None,
        notifier: Notifier | None = None,
        call_placer: CallPlacer | None = None,
        clock: "_Clock | None" = None,
    ) -> None:
        self._analyzer_config = analyzer_config or AnalyzerConfig()
        self._notifier = notifier or LoggingNotifier()
        self._call_placer = call_placer
        self._clock = clock or _SystemClock()
        self._sessions: dict[str, CallSession] = {}
        self._store_lock = asyncio.Lock()

    async def start_call(self, request: DialRequest) -> DialResponse:
        """Create a session and ask the call placer to place the outbound call."""
        now = self._clock.now()
        session = CallSession(
            id=self._generate_session_id(),
            support_number=request.support_number,
            user_callback_number=request.user_callback_number,
            created_at=now,
            updated_at=now,
            analyzer=HoldAudioAnalyzer(self._analyzer_config),
        )
        async with self._store_lock:
            self._sessions[session.id] = session
        if self._call_placer is not None:
            session.twilio_call_sid = await self._call_placer.place_call(session=session)
            session.updated_at = self._clock.now()
        return DialResponse(session_id=session.id, twilio_call_sid=session.twilio_call_sid)

    def get_session(self, session_id: str) -> CallSession | None:
        return self._sessions.get(session_id)

    async def attach_twilio_call_sid(self, session_id: str, twilio_call_sid: str) -> None:
        session = self._sessions.get(session_id)
        if session is None:
            return
        async with session._lock:
            session.twilio_call_sid = twilio_call_sid
            session.updated_at = self._clock.now()

    async def ingest_frame(self, session_id: str, samples: np.ndarray) -> CallState | None:
        """Feed one frame into the session's analyzer and fire notifications.

        Returns the new call state, or ``None`` if the session is unknown.
        """
        session = self._sessions.get(session_id)
        if session is None:
            return None
        async with session._lock:
            decision = session.analyzer.process(samples)
            previous_state = session.state
            session.state = decision.state
            session.updated_at = self._clock.now()
            should_notify = (
                decision.state == CallState.HUMAN_DETECTED
                and previous_state != CallState.HUMAN_DETECTED
                and session.notified_at is None
            )
            if should_notify:
                session.notified_at = self._clock.now()
        if should_notify:
            await self._notifier.notify_human_detected(session)
        return session.state

    async def end_session(self, session_id: str) -> None:
        async with self._store_lock:
            self._sessions.pop(session_id, None)

    def _generate_session_id(self) -> str:
        return secrets.token_urlsafe(8)


class _Clock(Protocol):
    def now(self) -> datetime: ...


class _SystemClock:
    def now(self) -> datetime:
        return datetime.now(tz=timezone.utc)


__all__ = [
    "CallHoldController",
    "CallPlacer",
    "CallSession",
    "DialRequest",
    "DialResponse",
    "LoggingNotifier",
    "Notifier",
]
