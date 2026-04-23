"""HTTP + WebSocket handlers for the call-hold detector.

Routes:
  POST /calls                  -> start an outbound call session.
  GET  /calls/{session_id}     -> return current state for polling UIs.
  POST /calls/{session_id}/twiml -> Twilio webhook; returns dial or ringback TwiML.
  POST /calls/{session_id}/status -> Twilio status callback (best-effort log).
  WS   /calls/{session_id}/media  -> Twilio Media Streams audio ingest.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field

from src.backend.controller.call_hold_controller import (
    CallHoldController,
    DialRequest,
)
from src.backend.controller.hold_audio_analyzer import CallState
from src.backend.gateway.twilio.adapters import TwilioUrlBuilder
from src.backend.gateway.twilio.media_stream import parse_media_stream_message
from src.backend.gateway.twilio.twiml import (
    build_outbound_dial_twiml,
    build_ringback_twiml,
)

router = APIRouter(prefix="/calls", tags=["calls"])
call_router = router


class StartCallRequestDTO(BaseModel):
    """Body for ``POST /calls``."""

    support_number: str = Field(min_length=3, description="E.164 support line, e.g. +18005551212.")
    user_callback_number: str = Field(min_length=3, description="E.164 number to ring back.")


class StartCallResponseDTO(BaseModel):
    """Response for ``POST /calls``."""

    session_id: str
    twilio_call_sid: str | None


class CallStatusDTO(BaseModel):
    """Response for ``GET /calls/{session_id}``."""

    session_id: str
    state: CallState
    support_number: str
    user_callback_number: str
    twilio_call_sid: str | None
    notified: bool


def get_call_controller(request: Request) -> CallHoldController:
    controller = getattr(request.app.state, "call_hold_controller", None)
    if controller is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Call-hold detector is not configured.",
        )
    return controller


def get_url_builder(request: Request) -> TwilioUrlBuilder:
    builder = getattr(request.app.state, "twilio_url_builder", None)
    if builder is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Twilio URL builder is not configured.",
        )
    return builder


@router.post("", response_model=StartCallResponseDTO, status_code=status.HTTP_201_CREATED)
async def start_call(
    body: StartCallRequestDTO,
    controller: Annotated[CallHoldController, Depends(get_call_controller)],
) -> StartCallResponseDTO:
    response = await controller.start_call(
        DialRequest(
            support_number=body.support_number,
            user_callback_number=body.user_callback_number,
        )
    )
    return StartCallResponseDTO(
        session_id=response.session_id,
        twilio_call_sid=response.twilio_call_sid,
    )


@router.get("/{session_id}", response_model=CallStatusDTO)
async def get_call_status(
    session_id: str,
    controller: Annotated[CallHoldController, Depends(get_call_controller)],
) -> CallStatusDTO:
    session = controller.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown call session.")
    return CallStatusDTO(
        session_id=session.id,
        state=session.state,
        support_number=session.support_number,
        user_callback_number=session.user_callback_number,
        twilio_call_sid=session.twilio_call_sid,
        notified=session.notified_at is not None,
    )


@router.post("/{session_id}/twiml")
async def twiml_webhook(
    session_id: str,
    request: Request,
    controller: Annotated[CallHoldController, Depends(get_call_controller)],
    url_builder: Annotated[TwilioUrlBuilder, Depends(get_url_builder)],
) -> Response:
    """Serve TwiML back to Twilio.

    If ``?event=ringback`` is present, we return TwiML for the ring-back leg
    (the second call we placed to the user). Otherwise we return TwiML that
    starts the Media Stream and dials the support line.
    """
    session = controller.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown call session.")

    event = request.query_params.get("event")
    if event == "ringback":
        body = build_ringback_twiml("An agent is ready. Connecting you now.")
    else:
        body = build_outbound_dial_twiml(
            support_number=session.support_number,
            media_stream_ws_url=url_builder.media_stream_ws_url_for(session.id),
            call_session_id=session.id,
        )
    return Response(content=body, media_type="application/xml")


@router.post("/{session_id}/status", status_code=status.HTTP_204_NO_CONTENT)
async def twilio_status_callback(session_id: str, request: Request) -> Response:
    """Accept Twilio status callbacks. Logged at info level for now."""
    form = await request.form()
    call_status = form.get("CallStatus")
    call_sid = form.get("CallSid")
    controller = get_call_controller(request)
    if isinstance(call_sid, str):
        await controller.attach_twilio_call_sid(session_id, call_sid)
    if call_status in {"completed", "failed", "busy", "no-answer", "canceled"}:
        await controller.end_session(session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.websocket("/{session_id}/media")
async def media_stream_websocket(websocket: WebSocket, session_id: str) -> None:
    """Accept a Twilio Media Streams WebSocket and feed frames to the analyzer."""
    controller: CallHoldController | None = getattr(
        websocket.app.state, "call_hold_controller", None
    )
    if controller is None or controller.get_session(session_id) is None:
        await websocket.close(code=1011)
        return
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_text()
            frame = parse_media_stream_message(message)
            if frame is None:
                continue
            if frame.event == "stop":
                break
            if frame.is_media:
                await controller.ingest_frame(session_id, frame.samples)
    except WebSocketDisconnect:
        pass


__all__ = [
    "call_router",
    "get_call_controller",
    "get_url_builder",
    "router",
]
