"""Tests for the Twilio TwiML builders."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from src.backend.gateway.twilio.twiml import (
    build_outbound_dial_twiml,
    build_ringback_twiml,
)


def test_outbound_dial_includes_stream_and_dial() -> None:
    xml = build_outbound_dial_twiml(
        support_number="+18005551212",
        media_stream_ws_url="wss://example.ngrok.app/calls/abc/media",
        call_session_id="abc",
    )
    root = ET.fromstring(xml)
    assert root.tag == "Response"
    start = root.find("Start")
    assert start is not None
    stream = start.find("Stream")
    assert stream is not None
    assert stream.get("url") == "wss://example.ngrok.app/calls/abc/media"
    assert stream.get("track") == "both_tracks"
    parameter = stream.find("Parameter")
    assert parameter is not None
    assert parameter.get("name") == "call_session_id"
    assert parameter.get("value") == "abc"
    dial = root.find("Dial")
    assert dial is not None
    assert dial.text == "+18005551212"
    assert dial.get("answerOnBridge") == "true"


def test_ringback_wraps_message_in_say_verb() -> None:
    xml = build_ringback_twiml("An agent is on the line. Please hold.")
    root = ET.fromstring(xml)
    assert root.tag == "Response"
    say = root.find("Say")
    assert say is not None
    assert say.text == "An agent is on the line. Please hold."
    assert say.get("voice") == "Polly.Joanna"
