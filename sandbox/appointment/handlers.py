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


async def handle_get_appointments(controller) -> dict:
    appointments = await controller.get_appointments()
    return {"status": "ok", "appointments": appointments}


async def handle_get_appointment(controller, appointment_id: int) -> dict:
    appointment = await controller.get_appointment(appointment_id)
    if appointment is None:
        return {"status": "error", "error": "appointment not found"}
    return {"status": "ok", "appointment": appointment}


async def handle_update_appointment(
    controller, appointment_id: int, payload: dict
) -> dict:
    try:
        appointment = await controller.update_appointment(
            appointment_id=appointment_id,
            title=payload.get("title"),
            start_time=(
                _as_datetime(payload["start_time"]) if "start_time" in payload else None
            ),
            end_time=_as_datetime(payload["end_time"])
            if "end_time" in payload
            else None,
        )
    except ValueError as exc:
        return {"status": "error", "error": str(exc)}

    return {"status": "ok", "appointment": appointment}


async def handle_delete_appointment(controller, appointment_id: int) -> dict:
    try:
        deletion = await controller.delete_appointment(appointment_id)
    except ValueError as exc:
        return {"status": "error", "error": str(exc)}
    return {"status": "ok", **deletion}
