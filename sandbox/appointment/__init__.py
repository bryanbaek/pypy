"""Appointment workflow slice with repository, gateway, controller, and handlers."""

from sandbox.appointment.controller import AppointmentController
from sandbox.appointment.gateway import AppointmentGateway
from sandbox.appointment.handlers import (
    handle_create_appointment,
    handle_delete_appointment,
    handle_get_appointment,
    handle_get_appointments,
    handle_update_appointment,
)

__all__ = [
    "AppointmentController",
    "AppointmentGateway",
    "handle_create_appointment",
    "handle_delete_appointment",
    "handle_get_appointment",
    "handle_get_appointments",
    "handle_update_appointment",
]
