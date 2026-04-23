"""Tests for the call-hold session controller."""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pytest

from src.backend.controller.call_hold_controller import (
    CallHoldController,
    CallPlacer,
    CallSession,
    DialRequest,
    LoggingNotifier,
    Notifier,
)
from src.backend.controller.hold_audio_analyzer import (
    AnalyzerConfig,
    CallState,
    HoldAudioAnalyzer,
    VoiceActivityDetector,
)


class _AlwaysSpeechVad(VoiceActivityDetector):
    def is_speech(self, frame: np.ndarray, sample_rate_hz: int) -> bool:
        del frame, sample_rate_hz
        return True


class _NeverMusicDetector:
    def is_music(self, frame: np.ndarray, sample_rate_hz: int) -> bool:
        del frame, sample_rate_hz
        return False


class _RecordingNotifier(Notifier):
    def __init__(self) -> None:
        self.calls: list[CallSession] = []

    async def notify_human_detected(self, session: CallSession) -> None:
        self.calls.append(session)


class _StubCallPlacer(CallPlacer):
    def __init__(self, sid: str = "CA-stub") -> None:
        self._sid = sid
        self.placed_for: list[CallSession] = []

    async def place_call(self, *, session: CallSession) -> str:
        self.placed_for.append(session)
        return self._sid


def _make_controller(notifier: Notifier | None = None) -> CallHoldController:
    return CallHoldController(
        analyzer_config=AnalyzerConfig(speech_seconds_required=1.0),
        notifier=notifier or LoggingNotifier(),
    )


async def test_start_call_creates_session_and_invokes_placer() -> None:
    placer = _StubCallPlacer(sid="CA-xyz")
    controller = CallHoldController(
        analyzer_config=AnalyzerConfig(speech_seconds_required=1.0),
        call_placer=placer,
    )
    response = await controller.start_call(
        DialRequest(support_number="+18005551212", user_callback_number="+15555550111")
    )
    assert response.twilio_call_sid == "CA-xyz"
    session = controller.get_session(response.session_id)
    assert session is not None
    assert session.support_number == "+18005551212"
    assert session.user_callback_number == "+15555550111"
    assert session.twilio_call_sid == "CA-xyz"
    assert len(placer.placed_for) == 1


async def test_ingest_frame_transitions_state_and_fires_notifier_once() -> None:
    notifier = _RecordingNotifier()
    controller = _make_controller(notifier=notifier)
    response = await controller.start_call(
        DialRequest(support_number="+18005551212", user_callback_number="+15555550111")
    )
    session = controller.get_session(response.session_id)
    assert session is not None
    session.analyzer = HoldAudioAnalyzer(
        AnalyzerConfig(speech_seconds_required=1.0),
        vad=_AlwaysSpeechVad(),
        music_detector=_NeverMusicDetector(),
    )

    frame = np.full(800, 0.3, dtype=np.float32)
    final_state: CallState | None = None
    for _ in range(20):
        final_state = await controller.ingest_frame(response.session_id, frame)
        if final_state == CallState.HUMAN_DETECTED:
            break
    assert final_state == CallState.HUMAN_DETECTED
    assert len(notifier.calls) == 1
    for _ in range(5):
        await controller.ingest_frame(response.session_id, frame)
    assert len(notifier.calls) == 1


async def test_ingest_frame_on_unknown_session_returns_none() -> None:
    controller = _make_controller()
    result = await controller.ingest_frame("does-not-exist", np.zeros(10, dtype=np.float32))
    assert result is None


async def test_end_session_removes_session() -> None:
    controller = _make_controller()
    response = await controller.start_call(
        DialRequest(support_number="+18005551212", user_callback_number="+15555550111")
    )
    assert controller.get_session(response.session_id) is not None
    await controller.end_session(response.session_id)
    assert controller.get_session(response.session_id) is None


async def test_logging_notifier_records_events() -> None:
    notifier = LoggingNotifier()
    session = CallSession(
        id="abc",
        support_number="+18005551212",
        user_callback_number="+15555550111",
        created_at=datetime.now(tz=timezone.utc),
        updated_at=datetime.now(tz=timezone.utc),
    )
    await notifier.notify_human_detected(session)
    assert notifier.events == ["human detected on call abc -> +15555550111"]


@pytest.mark.parametrize("bad_request", [
    DialRequest(support_number="", user_callback_number="+15555550111"),
    DialRequest(support_number="+18005551212", user_callback_number=""),
])
async def test_controller_accepts_requests_without_validation(bad_request: DialRequest) -> None:
    controller = _make_controller()
    response = await controller.start_call(bad_request)
    session = controller.get_session(response.session_id)
    assert session is not None
