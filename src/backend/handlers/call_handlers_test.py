"""Tests for the call-hold HTTP handlers.

The WebSocket media-stream route is exercised in ``call_handlers_ws_test.py``
via ``TestClient``. Here we pin the REST surface only.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.backend.controller.call_hold_controller import (
    CallHoldController,
    CallPlacer,
    CallSession,
)
from src.backend.controller.hold_audio_analyzer import AnalyzerConfig, CallState
from src.backend.gateway.twilio.adapters import TwilioUrlBuilder
from src.backend.handlers.call_handlers import call_router


class _StubPlacer(CallPlacer):
    def __init__(self, sid: str = "CA-test") -> None:
        self._sid = sid

    async def place_call(self, *, session: CallSession) -> str:
        return self._sid


def _build_app() -> tuple[FastAPI, CallHoldController]:
    app = FastAPI()
    controller = CallHoldController(
        analyzer_config=AnalyzerConfig(speech_seconds_required=1.0),
        call_placer=_StubPlacer(sid="CA-fixture"),
    )
    app.state.call_hold_controller = controller
    app.state.twilio_url_builder = TwilioUrlBuilder(public_base_url="https://example.ngrok.app")
    app.include_router(call_router)
    return app, controller


def test_post_calls_creates_session_and_returns_sid() -> None:
    app, controller = _build_app()
    client = TestClient(app)
    response = client.post(
        "/calls",
        json={"support_number": "+18005551212", "user_callback_number": "+15555550111"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["twilio_call_sid"] == "CA-fixture"
    session_id = body["session_id"]
    session = controller.get_session(session_id)
    assert session is not None
    assert session.support_number == "+18005551212"


def test_get_call_status_returns_current_state() -> None:
    app, controller = _build_app()
    client = TestClient(app)
    response = client.post(
        "/calls",
        json={"support_number": "+18005551212", "user_callback_number": "+15555550111"},
    )
    session_id = response.json()["session_id"]
    status_response = client.get(f"/calls/{session_id}")
    assert status_response.status_code == 200
    body = status_response.json()
    assert body["session_id"] == session_id
    assert body["state"] == CallState.UNKNOWN.value
    assert body["notified"] is False
    assert body["twilio_call_sid"] == "CA-fixture"


def test_get_call_status_404_for_unknown() -> None:
    app, _ = _build_app()
    client = TestClient(app)
    response = client.get("/calls/does-not-exist")
    assert response.status_code == 404


def test_twiml_webhook_returns_outbound_dial_xml_by_default() -> None:
    app, _ = _build_app()
    client = TestClient(app)
    session_id = client.post(
        "/calls",
        json={"support_number": "+18005551212", "user_callback_number": "+15555550111"},
    ).json()["session_id"]
    response = client.post(f"/calls/{session_id}/twiml")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")
    body = response.text
    assert "<Stream" in body
    assert "+18005551212" in body
    assert "wss://example.ngrok.app" in body


def test_twiml_webhook_returns_ringback_when_event_query_is_set() -> None:
    app, _ = _build_app()
    client = TestClient(app)
    session_id = client.post(
        "/calls",
        json={"support_number": "+18005551212", "user_callback_number": "+15555550111"},
    ).json()["session_id"]
    response = client.post(f"/calls/{session_id}/twiml?event=ringback")
    assert response.status_code == 200
    body = response.text
    assert "<Say" in body
    assert "<Stream" not in body


def test_twiml_webhook_404_for_unknown_session() -> None:
    app, _ = _build_app()
    client = TestClient(app)
    response = client.post("/calls/nope/twiml")
    assert response.status_code == 404


def test_status_callback_ends_session_on_completed() -> None:
    app, controller = _build_app()
    client = TestClient(app)
    session_id = client.post(
        "/calls",
        json={"support_number": "+18005551212", "user_callback_number": "+15555550111"},
    ).json()["session_id"]
    response = client.post(
        f"/calls/{session_id}/status",
        data={"CallStatus": "completed", "CallSid": "CA-new"},
    )
    assert response.status_code == 204
    assert controller.get_session(session_id) is None


def test_status_callback_ignores_non_terminal_status() -> None:
    app, controller = _build_app()
    client = TestClient(app)
    session_id = client.post(
        "/calls",
        json={"support_number": "+18005551212", "user_callback_number": "+15555550111"},
    ).json()["session_id"]
    response = client.post(
        f"/calls/{session_id}/status",
        data={"CallStatus": "ringing", "CallSid": "CA-new"},
    )
    assert response.status_code == 204
    session = controller.get_session(session_id)
    assert session is not None
    assert session.twilio_call_sid == "CA-new"
