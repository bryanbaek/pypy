"""Thin Twilio REST wrapper for placing calls and sending SMS.

Kept small and synchronous: the controller awaits ``asyncio.to_thread`` when
it invokes these methods. The real Twilio SDK is imported lazily so unit
tests can instantiate the client with an injected stub.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class TwilioCredentials:
    """Credentials + default from-number for outbound Twilio traffic."""

    account_sid: str
    auth_token: str
    from_number: str


class _TwilioRestClient(Protocol):
    """Minimal slice of the ``twilio.rest.Client`` surface we rely on."""

    @property
    def calls(self) -> Any: ...

    @property
    def messages(self) -> Any: ...


def _build_default_client(credentials: TwilioCredentials) -> _TwilioRestClient:
    """Create a real ``twilio.rest.Client``. Imported lazily to keep tests light."""
    from twilio.rest import Client

    return Client(credentials.account_sid, credentials.auth_token)


@dataclass(frozen=True)
class PlacedCall:
    """Result of a successful outbound dial."""

    sid: str
    to: str
    from_: str


@dataclass(frozen=True)
class SentSms:
    """Result of a successful SMS send."""

    sid: str
    to: str


class TwilioClient:
    """Wrap the Twilio REST client with the narrow ops the detector needs."""

    def __init__(
        self,
        credentials: TwilioCredentials,
        *,
        rest_client: _TwilioRestClient | None = None,
    ) -> None:
        self._credentials = credentials
        self._rest_client = rest_client or _build_default_client(credentials)

    @property
    def from_number(self) -> str:
        return self._credentials.from_number

    def place_outbound_call(
        self,
        *,
        to_number: str,
        twiml_url: str,
        status_callback_url: str | None = None,
    ) -> PlacedCall:
        """Place an outbound call. Twilio will hit ``twiml_url`` on answer."""
        kwargs: dict[str, object] = {
            "to": to_number,
            "from_": self._credentials.from_number,
            "url": twiml_url,
        }
        if status_callback_url:
            kwargs["status_callback"] = status_callback_url
            kwargs["status_callback_event"] = ["initiated", "ringing", "answered", "completed"]
        call = self._rest_client.calls.create(**kwargs)
        return PlacedCall(sid=call.sid, to=to_number, from_=self._credentials.from_number)

    def send_sms(self, *, to_number: str, body: str) -> SentSms:
        """Send an SMS from the configured ``from_number``."""
        message = self._rest_client.messages.create(
            to=to_number,
            from_=self._credentials.from_number,
            body=body,
        )
        return SentSms(sid=message.sid, to=to_number)


def build_twilio_client(credentials: TwilioCredentials) -> TwilioClient:
    """Construct a default Twilio client with real credentials."""
    return TwilioClient(credentials)


__all__ = [
    "PlacedCall",
    "SentSms",
    "TwilioClient",
    "TwilioCredentials",
    "build_twilio_client",
]
