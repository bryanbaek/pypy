"""Decoder for Twilio Media Streams WebSocket frames.

Twilio sends JSON messages over the WebSocket. The ``media`` event carries a
base64-encoded payload of µ-law-encoded (G.711) 8 kHz mono samples, one 20 ms
chunk at a time (160 bytes per frame). See:
https://www.twilio.com/docs/voice/twiml/stream#message-media

This module is dependency-free so the analyzer can run without the ``twilio``
SDK; it only parses the JSON envelope and converts µ-law bytes to PCM16
floats that the analyzer consumes.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass

import numpy as np

_ULAW_DECODE_TABLE: np.ndarray | None = None


def _build_ulaw_decode_table() -> np.ndarray:
    """Return a lookup table that maps every µ-law byte value to PCM16.

    Derived from ITU-T G.711 µ-law. Built once at import time, cached.
    """
    table = np.zeros(256, dtype=np.int16)
    for byte in range(256):
        u = ~byte & 0xFF
        sign = u & 0x80
        exponent = (u >> 4) & 0x07
        mantissa = u & 0x0F
        magnitude = ((mantissa << 3) + 0x84) << exponent
        magnitude -= 0x84
        table[byte] = -magnitude if sign else magnitude
    return table


def _get_decode_table() -> np.ndarray:
    global _ULAW_DECODE_TABLE
    if _ULAW_DECODE_TABLE is None:
        _ULAW_DECODE_TABLE = _build_ulaw_decode_table()
    return _ULAW_DECODE_TABLE


def ulaw_bytes_to_pcm16_float(payload: bytes) -> np.ndarray:
    """Decode µ-law bytes to PCM16 normalized to float32 in [-1, 1]."""
    if not payload:
        return np.zeros(0, dtype=np.float32)
    table = _get_decode_table()
    indices = np.frombuffer(payload, dtype=np.uint8)
    pcm16 = table[indices]
    return pcm16.astype(np.float32) / 32768.0


@dataclass(frozen=True)
class MediaStreamFrame:
    """A parsed Twilio Media Streams ``media`` event."""

    event: str
    stream_sid: str | None
    call_session_id: str | None
    track: str | None
    samples: np.ndarray
    sequence_number: int | None

    @property
    def is_media(self) -> bool:
        return self.event == "media" and self.samples.size > 0


def parse_media_stream_message(message: str | bytes) -> MediaStreamFrame | None:
    """Parse a WebSocket text frame from Twilio Media Streams.

    Returns ``None`` for events the analyzer does not care about
    (``connected``, ``mark``). Returns a populated frame for ``start`` and
    ``media`` events; the ``start`` event has an empty ``samples`` array but
    carries the ``call_session_id`` custom parameter.
    """
    if isinstance(message, bytes):
        message = message.decode("utf-8")
    try:
        data = json.loads(message)
    except json.JSONDecodeError:
        return None
    event = data.get("event")
    if event not in {"start", "media", "stop"}:
        return None

    stream_sid = data.get("streamSid")
    call_session_id: str | None = None
    track: str | None = None
    samples = np.zeros(0, dtype=np.float32)
    sequence_number: int | None = None

    if event == "start":
        start = data.get("start", {})
        custom_parameters = start.get("customParameters", {})
        call_session_id = custom_parameters.get("call_session_id")
        track = start.get("tracks", [None])[0] if start.get("tracks") else None
    elif event == "media":
        media = data.get("media", {})
        payload = media.get("payload", "")
        if payload:
            samples = ulaw_bytes_to_pcm16_float(base64.b64decode(payload))
        track = media.get("track")
        raw_seq = media.get("chunk")
        sequence_number = int(raw_seq) if raw_seq is not None else None

    return MediaStreamFrame(
        event=event,
        stream_sid=stream_sid,
        call_session_id=call_session_id,
        track=track,
        samples=samples,
        sequence_number=sequence_number,
    )


__all__ = [
    "MediaStreamFrame",
    "parse_media_stream_message",
    "ulaw_bytes_to_pcm16_float",
]
