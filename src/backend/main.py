"""FastAPI application entrypoint for local and containerized runs."""

import os

from fastapi import FastAPI

from src.backend.controller.call_hold_controller import (
    CallHoldController,
    LoggingNotifier,
)
from src.backend.controller.hold_audio_analyzer import AnalyzerConfig
from src.backend.controller.job_controller import build_job_controller
from src.backend.gateway.twilio.adapters import (
    TwilioCallPlacer,
    TwilioNotifier,
    TwilioUrlBuilder,
)
from src.backend.gateway.twilio.client import TwilioCredentials, build_twilio_client
from src.backend.handlers.call_handlers import call_router
from src.backend.handlers.job_handlers import job_router


def _build_analyzer_config() -> AnalyzerConfig:
    def _float_env(key: str, default: float) -> float:
        value = os.getenv(key)
        if not value:
            return default
        try:
            return float(value)
        except ValueError:
            return default

    return AnalyzerConfig(
        speech_seconds_required=_float_env("CALL_HOLD_VAD_SPEECH_SECONDS", 8.0),
        music_required_prior_seconds=_float_env("CALL_HOLD_MUSIC_REQUIRED_SECONDS", 0.0),
        fingerprint_buffer_seconds=_float_env("CALL_HOLD_FINGERPRINT_BUFFER_SECONDS", 300.0),
    )


def _build_call_hold_controller() -> tuple[CallHoldController, TwilioUrlBuilder]:
    """Construct the call-hold controller with Twilio adapters when configured.

    When Twilio credentials or the public base URL are missing, fall back to a
    logging notifier so the module still imports cleanly for local tests.
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    from_number = os.getenv("TWILIO_FROM_NUMBER", "").strip()
    public_base_url = os.getenv("PUBLIC_BASE_URL", "").strip() or "http://localhost:8000"
    url_builder = TwilioUrlBuilder(public_base_url=public_base_url)

    analyzer_config = _build_analyzer_config()
    if not (account_sid and auth_token and from_number):
        return (
            CallHoldController(
                analyzer_config=analyzer_config,
                notifier=LoggingNotifier(),
            ),
            url_builder,
        )
    twilio_client = build_twilio_client(
        TwilioCredentials(
            account_sid=account_sid,
            auth_token=auth_token,
            from_number=from_number,
        )
    )
    return (
        CallHoldController(
            analyzer_config=analyzer_config,
            notifier=TwilioNotifier(twilio_client=twilio_client, url_builder=url_builder),
            call_placer=TwilioCallPlacer(twilio_client=twilio_client, url_builder=url_builder),
        ),
        url_builder,
    )


def create_app() -> FastAPI:
    """Create the FastAPI application used by local workflows."""
    application = FastAPI(
        title="FastAPI Template",
        description="Local entrypoint for the reusable FastAPI template.",
    )
    application.state.job_controller = build_job_controller()
    call_controller, url_builder = _build_call_hold_controller()
    application.state.call_hold_controller = call_controller
    application.state.twilio_url_builder = url_builder

    @application.get("/")
    async def read_root() -> dict[str, str]:
        """Return a minimal landing payload for the template app."""
        return {"message": "Welcome to the FastAPI template"}

    @application.get("/health")
    async def read_health() -> dict[str, str]:
        """Return the process health status."""
        return {"status": "ok"}

    application.include_router(job_router)
    application.include_router(call_router)

    return application


app = create_app()


__all__ = ["app", "create_app"]
