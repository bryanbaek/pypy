"""Tests for the Twilio Media Streams parser and µ-law decoder."""

from __future__ import annotations

import base64
import json

import numpy as np

from src.backend.gateway.twilio.media_stream import (
    parse_media_stream_message,
    ulaw_bytes_to_pcm16_float,
)

# Reference vectors from the ITU-T G.711 spec: µ-law bytes and the PCM16
# samples they decode to. These pin the decode table against spec drift.
# Source derivation: ((~byte)&0xFF), sign bit, 3-bit exponent, 4-bit mantissa.
ULAW_REFERENCE = [
    (0xFF, 0),  # positive silence.
    (0x7F, 0),  # negative silence (bit-complement of 0xFF is 0x00, sign=1).
    (0x80, 32124),  # most-positive sample after complement + sign/exp/mantissa expansion.
    (0x00, -32124),  # most-negative sample.
]


def test_ulaw_decoder_matches_reference_vectors() -> None:
    for byte, expected in ULAW_REFERENCE:
        decoded = ulaw_bytes_to_pcm16_float(bytes([byte]))
        assert decoded.shape == (1,)
        assert abs(decoded[0] * 32768.0 - expected) <= 1


def test_ulaw_decoder_handles_empty_payload() -> None:
    result = ulaw_bytes_to_pcm16_float(b"")
    assert result.shape == (0,)
    assert result.dtype == np.float32


def test_parse_start_event_extracts_custom_parameters() -> None:
    message = json.dumps(
        {
            "event": "start",
            "streamSid": "MZ123",
            "start": {
                "tracks": ["inbound"],
                "customParameters": {"call_session_id": "call-abc"},
            },
        }
    )
    frame = parse_media_stream_message(message)
    assert frame is not None
    assert frame.event == "start"
    assert frame.stream_sid == "MZ123"
    assert frame.call_session_id == "call-abc"
    assert frame.track == "inbound"
    assert frame.samples.size == 0


def test_parse_media_event_decodes_payload() -> None:
    raw_bytes = bytes([0xFF, 0x7F, 0x80, 0x00])
    message = json.dumps(
        {
            "event": "media",
            "streamSid": "MZ123",
            "media": {
                "payload": base64.b64encode(raw_bytes).decode("ascii"),
                "track": "inbound",
                "chunk": "42",
            },
        }
    )
    frame = parse_media_stream_message(message)
    assert frame is not None
    assert frame.event == "media"
    assert frame.is_media
    assert frame.track == "inbound"
    assert frame.sequence_number == 42
    assert frame.samples.shape == (4,)
    assert frame.samples.dtype == np.float32


def test_parse_unknown_event_returns_none() -> None:
    assert parse_media_stream_message(json.dumps({"event": "connected"})) is None


def test_parse_malformed_json_returns_none() -> None:
    assert parse_media_stream_message("not json") is None


def test_parse_accepts_bytes_payload() -> None:
    message = json.dumps({"event": "stop", "streamSid": "MZ1"}).encode("utf-8")
    frame = parse_media_stream_message(message)
    assert frame is not None
    assert frame.event == "stop"
