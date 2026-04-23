"""Tests for the Twilio REST client wrapper."""

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any

from src.backend.gateway.twilio.client import TwilioClient, TwilioCredentials


@dataclass
class _RecordedCall:
    kwargs: dict[str, Any]


class _StubCallsResource:
    def __init__(self, sid: str) -> None:
        self._sid = sid
        self.recorded: list[_RecordedCall] = []

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.recorded.append(_RecordedCall(kwargs=kwargs))
        return SimpleNamespace(sid=self._sid)


class _StubMessagesResource:
    def __init__(self, sid: str) -> None:
        self._sid = sid
        self.recorded: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.recorded.append(kwargs)
        return SimpleNamespace(sid=self._sid)


class _StubRestClient:
    def __init__(self, call_sid: str, message_sid: str) -> None:
        self.calls = _StubCallsResource(call_sid)
        self.messages = _StubMessagesResource(message_sid)


def _credentials() -> TwilioCredentials:
    return TwilioCredentials(
        account_sid="ACtest",
        auth_token="token",
        from_number="+15555550100",
    )


def test_place_outbound_call_posts_to_calls_resource() -> None:
    rest = _StubRestClient(call_sid="CA123", message_sid="SM999")
    client = TwilioClient(_credentials(), rest_client=rest)
    placed = client.place_outbound_call(
        to_number="+18005551212",
        twiml_url="https://example.ngrok.app/calls/abc/twiml",
        status_callback_url="https://example.ngrok.app/calls/abc/status",
    )
    assert placed.sid == "CA123"
    assert placed.to == "+18005551212"
    assert placed.from_ == "+15555550100"
    recorded = rest.calls.recorded[0].kwargs
    assert recorded["to"] == "+18005551212"
    assert recorded["from_"] == "+15555550100"
    assert recorded["url"] == "https://example.ngrok.app/calls/abc/twiml"
    assert recorded["status_callback"] == "https://example.ngrok.app/calls/abc/status"
    assert "initiated" in recorded["status_callback_event"]


def test_place_outbound_call_omits_status_when_not_provided() -> None:
    rest = _StubRestClient(call_sid="CA123", message_sid="SM999")
    client = TwilioClient(_credentials(), rest_client=rest)
    client.place_outbound_call(
        to_number="+18005551212",
        twiml_url="https://example.ngrok.app/calls/abc/twiml",
    )
    recorded = rest.calls.recorded[0].kwargs
    assert "status_callback" not in recorded
    assert "status_callback_event" not in recorded


def test_send_sms_uses_configured_from_number() -> None:
    rest = _StubRestClient(call_sid="CA123", message_sid="SM999")
    client = TwilioClient(_credentials(), rest_client=rest)
    sent = client.send_sms(to_number="+15555550111", body="Human picked up")
    assert sent.sid == "SM999"
    assert sent.to == "+15555550111"
    recorded = rest.messages.recorded[0]
    assert recorded["to"] == "+15555550111"
    assert recorded["from_"] == "+15555550100"
    assert recorded["body"] == "Human picked up"
