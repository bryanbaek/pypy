"""Adapters that implement controller Protocols on top of Twilio.

Keeps the controller free of Twilio imports: ``CallHoldController`` only
depends on the ``CallPlacer`` and ``Notifier`` Protocols it defines, and
these classes plug real Twilio behavior behind those interfaces.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from src.backend.controller.call_hold_controller import (
    CallPlacer,
    CallSession,
    Notifier,
)
from src.backend.gateway.twilio.client import TwilioClient

DEFAULT_SMS_BODY = "A human just picked up. We're ringing you back now."


@dataclass(frozen=True)
class TwilioUrlBuilder:
    """Compose the webhook URLs Twilio needs to reach us.

    ``public_base_url`` must be a publicly reachable HTTPS URL (ngrok or a
    real deploy). During local development point this at your ngrok tunnel.
    """

    public_base_url: str

    @property
    def _http_base(self) -> str:
        return self.public_base_url.rstrip("/")

    @property
    def _ws_base(self) -> str:
        base = self._http_base
        if base.startswith("https://"):
            return "wss://" + base[len("https://") :]
        if base.startswith("http://"):
            return "ws://" + base[len("http://") :]
        return base

    def twiml_url_for(self, session_id: str) -> str:
        return f"{self._http_base}/calls/{session_id}/twiml"

    def media_stream_ws_url_for(self, session_id: str) -> str:
        return f"{self._ws_base}/calls/{session_id}/media"

    def status_callback_url_for(self, session_id: str) -> str:
        return f"{self._http_base}/calls/{session_id}/status"


class TwilioCallPlacer(CallPlacer):
    """Place the outbound call via Twilio."""

    def __init__(self, *, twilio_client: TwilioClient, url_builder: TwilioUrlBuilder) -> None:
        self._twilio_client = twilio_client
        self._url_builder = url_builder

    async def place_call(self, *, session: CallSession) -> str:
        def _place() -> str:
            placed = self._twilio_client.place_outbound_call(
                to_number=session.support_number,
                twiml_url=self._url_builder.twiml_url_for(session.id),
                status_callback_url=self._url_builder.status_callback_url_for(session.id),
            )
            return placed.sid

        return await asyncio.to_thread(_place)


class TwilioNotifier(Notifier):
    """Notify the user via SMS + ring-back."""

    def __init__(
        self,
        *,
        twilio_client: TwilioClient,
        url_builder: TwilioUrlBuilder,
        sms_body: str = DEFAULT_SMS_BODY,
    ) -> None:
        self._twilio_client = twilio_client
        self._url_builder = url_builder
        self._sms_body = sms_body

    async def notify_human_detected(self, session: CallSession) -> None:
        def _send_sms() -> None:
            self._twilio_client.send_sms(
                to_number=session.user_callback_number,
                body=self._sms_body,
            )

        def _place_ringback() -> None:
            self._twilio_client.place_outbound_call(
                to_number=session.user_callback_number,
                twiml_url=self._url_builder.twiml_url_for(session.id) + "?event=ringback",
            )

        await asyncio.gather(
            asyncio.to_thread(_send_sms),
            asyncio.to_thread(_place_ringback),
        )


__all__ = ["TwilioCallPlacer", "TwilioNotifier", "TwilioUrlBuilder"]
