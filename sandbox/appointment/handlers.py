from datetime import datetime


def _as_datetime(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    raise ValueError("start_time and end_time must be datetime or ISO datetime strings")


async def handle_create_appointment(controller, payload: dict) -> dict:
    try:
        appointment = await controller.create_appointment(
            title=payload["title"],
            start_time=_as_datetime(payload["start_time"]),
            end_time=_as_datetime(payload["end_time"]),
        )
    except (KeyError, ValueError) as exc:
        return {"status": "error", "error": str(exc)}

    return {"status": "ok", "appointment": appointment}
