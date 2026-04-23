"""TwiML builders for the call-hold detector.

Kept as a small module so tests can assert on exact XML output without
importing the full ``twilio`` SDK. The Twilio REST client is used for
placing the call; TwiML XML is served back to Twilio when it hits our
voice webhook.
"""

from __future__ import annotations

from xml.etree.ElementTree import Element, SubElement, tostring


def build_outbound_dial_twiml(
    *,
    support_number: str,
    media_stream_ws_url: str,
    call_session_id: str,
) -> str:
    """Return TwiML that answers the outbound-dial webhook.

    The returned verbs:
      1. Open a bidirectional Media Stream to ``media_stream_ws_url`` so we
         receive audio frames from the support-line leg in real time.
      2. Dial the support number. Twilio connects the Media Stream to the
         conferenced call audio, which is what the analyzer consumes.

    The ``call_session_id`` is passed as a custom Media Stream parameter so
    the WebSocket handler can associate inbound frames with the session.
    """
    response = Element("Response")
    start = SubElement(response, "Start")
    stream = SubElement(start, "Stream", {"url": media_stream_ws_url, "track": "both_tracks"})
    SubElement(stream, "Parameter", {"name": "call_session_id", "value": call_session_id})
    dial = SubElement(response, "Dial", {"answerOnBridge": "true"})
    dial.text = support_number
    return tostring(response, encoding="unicode", xml_declaration=True)


def build_ringback_twiml(message: str) -> str:
    """Return TwiML that greets the user when we ring them back.

    Played on the user-callback leg after we detect a human on the support
    leg. The user hears a short spoken summary, then the two legs are
    bridged via a Twilio Conference in the controller.
    """
    response = Element("Response")
    say = SubElement(response, "Say", {"voice": "Polly.Joanna"})
    say.text = message
    return tostring(response, encoding="unicode", xml_declaration=True)


__all__ = ["build_outbound_dial_twiml", "build_ringback_twiml"]
