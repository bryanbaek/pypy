"""WebSocket test for the Media Streams endpoint.

End-to-end-ish: feeds enough synthetic speech frames to trip the analyzer
into HUMAN_DETECTED and verifies the HTTP status endpoint reflects it.
"""

from __future__ import annotations

import base64
import json

import numpy as np
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.backend.controller.call_hold_controller import (
    CallHoldController,
    CallPlacer,
    CallSession,
    LoggingNotifier,
)
from src.backend.controller.hold_audio_analyzer import (
    AnalyzerConfig,
    HoldAudioAnalyzer,
    VoiceActivityDetector,
)
from src.backend.gateway.twilio.adapters import TwilioUrlBuilder
from src.backend.handlers.call_handlers import call_router


class _AlwaysSpeech(VoiceActivityDetector):
    def is_speech(self, frame: np.ndarray, sample_rate_hz: int) -> bool:
        del frame, sample_rate_hz
        return True


class _NeverMusic:
    def is_music(self, frame: np.ndarray, sample_rate_hz: int) -> bool:
        del frame, sample_rate_hz
        return False


class _StubPlacer(CallPlacer):
    async def place_call(self, *, session: CallSession) -> str:
        return "CA-ws"


def _ulaw_encoded_silence_bytes(samples: int = 160) -> bytes:
    """160 µ-law bytes = one 20 ms frame of zero samples at 8 kHz."""
    return bytes([0xFF] * samples)


def _media_event_message(stream_sid: str, payload: bytes) -> str:
    return json.dumps(
        {
            "event": "media",
            "streamSid": stream_sid,
            "media": {
                "payload": base64.b64encode(payload).decode("ascii"),
                "track": "inbound",
                "chunk": "1",
            },
        }
    )


def test_media_stream_ws_drives_analyzer_to_human_detected() -> None:
    app = FastAPI()
    notifier = LoggingNotifier()
    controller = CallHoldController(
        analyzer_config=AnalyzerConfig(speech_seconds_required=1.0),
        call_placer=_StubPlacer(),
        notifier=notifier,
    )
    app.state.call_hold_controller = controller
    app.state.twilio_url_builder = TwilioUrlBuilder(public_base_url="https://example.ngrok.app")
    app.include_router(call_router)
    client = TestClient(app)
    session_id = client.post(
        "/calls",
        json={"support_number": "+18005551212", "user_callback_number": "+15555550111"},
    ).json()["session_id"]
    session = controller.get_session(session_id)
    assert session is not None
    session.analyzer = HoldAudioAnalyzer(
        AnalyzerConfig(speech_seconds_required=1.0),
        vad=_AlwaysSpeech(),
        music_detector=_NeverMusic(),
    )

    with client.websocket_connect(f"/calls/{session_id}/media") as ws:
        start_msg = {
            "event": "start",
            "streamSid": "MZ-test",
            "start": {
                "tracks": ["inbound"],
                "customParameters": {"call_session_id": session_id},
            },
        }
        ws.send_text(json.dumps(start_msg))
        for _ in range(120):
            ws.send_text(_media_event_message("MZ-test", _ulaw_encoded_silence_bytes()))
        ws.send_text(json.dumps({"event": "stop", "streamSid": "MZ-test"}))

    assert len(notifier.events) == 1
    status_response = client.get(f"/calls/{session_id}")
    assert status_response.status_code == 200
    assert status_response.json()["state"] == "human_detected"
    assert status_response.json()["notified"] is True


def test_media_stream_ws_rejects_unknown_session() -> None:
    app = FastAPI()
    app.state.call_hold_controller = CallHoldController()
    app.state.twilio_url_builder = TwilioUrlBuilder(public_base_url="https://example.ngrok.app")
    app.include_router(call_router)
    client = TestClient(app)
    from starlette.websockets import WebSocketDisconnect

    try:
        with client.websocket_connect("/calls/nope/media"):
            raise AssertionError("WebSocket connect should have been rejected")
    except WebSocketDisconnect as exc:
        assert exc.code == 1011
