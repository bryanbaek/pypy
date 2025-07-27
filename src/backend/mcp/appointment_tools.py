"""
Appointment tools for the MCP booking server.
Handles appointment creation, deletion, scheduling, and availability checking.
"""

import json
from datetime import datetime
from typing import Dict, List
import uuid

from mcp import types


class AppointmentTools:
    """Tools for managing appointments."""

    def __init__(self, appointments_data: List[Dict], data_dir: str):
        self.appointments_data = appointments_data
        self.data_dir = data_dir

    def get_tool_definitions(self) -> List[types.Tool]:
        """Get appointment tool definitions."""
        return [
            types.Tool(
                name="create_appointment",
                description="Create a new appointment for a customer",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "customer_name": {
                            "type": "string",
                            "description": "Name of the customer",
                        },
                        "customer_email": {
                            "type": "string",
                            "description": "Email address of the customer",
                        },
                        "service_type": {
                            "type": "string",
                            "description": "Type of service (consultation, health_checkup, therapy_session)",
                        },
                        "date": {
                            "type": "string",
                            "description": "Date for the appointment (YYYY-MM-DD format)",
                        },
                        "time": {
                            "type": "string",
                            "description": "Time for the appointment (HH:MM format, 9 AM to 5 PM)",
                        },
                        "notes": {
                            "type": "string",
                            "description": "Additional notes for the appointment",
                        },
                    },
                    "required": [
                        "customer_name",
                        "customer_email",
                        "service_type",
                        "date",
                        "time",
                    ],
                },
            ),
            types.Tool(
                name="delete_appointment",
                description="Delete an existing appointment",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "appointment_id": {
                            "type": "string",
                            "description": "ID of the appointment to delete",
                        }
                    },
                    "required": ["appointment_id"],
                },
            ),
            types.Tool(
                name="get_available_slots",
                description="Get available appointment slots for a specific date",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "Date to check availability (YYYY-MM-DD format)",
                        },
                        "service_type": {
                            "type": "string",
                            "description": "Optional: Filter by service type",
                        },
                    },
                    "required": ["date"],
                },
            ),
            types.Tool(
                name="list_appointments",
                description="List appointments with optional filtering",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "date": {
                            "type": "string",
                            "description": "Optional: Filter by specific date (YYYY-MM-DD)",
                        },
                        "customer_email": {
                            "type": "string",
                            "description": "Optional: Filter by customer email",
                        },
                        "service_type": {
                            "type": "string",
                            "description": "Optional: Filter by service type",
                        },
                        "status": {
                            "type": "string",
                            "description": "Optional: Filter by status (scheduled, completed, cancelled)",
                        },
                    },
                    "required": [],
                },
            ),
        ]

    async def create_appointment(self, args: dict) -> str:
        """Create a new appointment."""
        try:
            # Validate required fields
            required_fields = [
                "customer_name",
                "customer_email",
                "service_type",
                "date",
                "time",
            ]
            for field in required_fields:
                if field not in args:
                    return f"Error: Missing required field '{field}'"

            # Validate date format
            try:
                appointment_date = datetime.strptime(args["date"], "%Y-%m-%d").date()
            except ValueError:
                return "Error: Invalid date format. Use YYYY-MM-DD"

            # Validate time format and business hours
            try:
                appointment_time = datetime.strptime(args["time"], "%H:%M").time()
                if appointment_time.hour < 9 or appointment_time.hour >= 17:
                    return "Error: Appointment time must be between 9:00 AM and 5:00 PM"
            except ValueError:
                return "Error: Invalid time format. Use HH:MM"

            # Check if slot is available
            appointment_datetime = datetime.combine(appointment_date, appointment_time)
            for existing_appointment in self.appointments_data:
                existing_datetime = datetime.fromisoformat(
                    existing_appointment["appointment_datetime"]
                )
                if existing_datetime == appointment_datetime:
                    return "Error: This time slot is already booked"

            # Create new appointment
            new_appointment = {
                "id": str(uuid.uuid4()),
                "customer_name": args["customer_name"],
                "customer_email": args["customer_email"],
                "service_type": args["service_type"],
                "appointment_datetime": appointment_datetime.isoformat(),
                "status": "scheduled",
                "notes": args.get("notes", ""),
                "created_at": datetime.now().isoformat(),
            }

            self.appointments_data.append(new_appointment)

            return json.dumps(
                {
                    "success": True,
                    "message": "Appointment created successfully",
                    "appointment": new_appointment,
                },
                indent=2,
            )

        except Exception as e:
            return f"Error creating appointment: {str(e)}"

    async def delete_appointment(self, args: dict) -> str:
        """Delete an existing appointment."""
        try:
            appointment_id = args.get("appointment_id")
            if not appointment_id:
                return "Error: Missing appointment_id"

            for i, appointment in enumerate(self.appointments_data):
                if appointment["id"] == appointment_id:
                    deleted_appointment = self.appointments_data.pop(i)
                    return json.dumps(
                        {
                            "success": True,
                            "message": "Appointment deleted successfully",
                            "deleted_appointment": deleted_appointment,
                        },
                        indent=2,
                    )

            return "Error: Appointment not found"

        except Exception as e:
            return f"Error deleting appointment: {str(e)}"

    async def get_available_slots(self, args: dict) -> str:
        """Get available appointment slots for a specific date."""
        try:
            date_str = args.get("date")
            if not date_str:
                return "Error: Missing date parameter"

            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return "Error: Invalid date format. Use YYYY-MM-DD"

            # Generate all possible time slots (9 AM to 5 PM, hourly)
            all_slots = []
            for hour in range(9, 17):  # 9 AM to 4 PM (last slot)
                slot_time = f"{hour:02d}:00"
                all_slots.append(slot_time)

            # Find booked slots for the target date
            booked_slots = []
            for appointment in self.appointments_data:
                appointment_datetime = datetime.fromisoformat(
                    appointment["appointment_datetime"]
                )
                if appointment_datetime.date() == target_date:
                    booked_slots.append(appointment_datetime.strftime("%H:%M"))

            # Calculate available slots
            available_slots = [slot for slot in all_slots if slot not in booked_slots]

            # Filter by service type if provided
            service_type = args.get("service_type")
            result = {
                "date": date_str,
                "available_slots": available_slots,
                "booked_slots": booked_slots,
                "total_available": len(available_slots),
            }

            if service_type:
                result["service_type"] = service_type

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error getting available slots: {str(e)}"

    async def list_appointments(self, args: dict) -> str:
        """List appointments with optional filtering."""
        try:
            filtered_appointments = list(self.appointments_data)

            # Apply filters
            if "date" in args:
                try:
                    filter_date = datetime.strptime(args["date"], "%Y-%m-%d").date()
                    filtered_appointments = [
                        apt
                        for apt in filtered_appointments
                        if datetime.fromisoformat(apt["appointment_datetime"]).date()
                        == filter_date
                    ]
                except ValueError:
                    return "Error: Invalid date format. Use YYYY-MM-DD"

            if "customer_email" in args:
                filtered_appointments = [
                    apt
                    for apt in filtered_appointments
                    if apt["customer_email"].lower() == args["customer_email"].lower()
                ]

            if "service_type" in args:
                filtered_appointments = [
                    apt
                    for apt in filtered_appointments
                    if apt["service_type"] == args["service_type"]
                ]

            if "status" in args:
                filtered_appointments = [
                    apt
                    for apt in filtered_appointments
                    if apt["status"] == args["status"]
                ]

            # Sort by appointment datetime
            filtered_appointments.sort(key=lambda x: x["appointment_datetime"])

            result = {
                "total_appointments": len(filtered_appointments),
                "appointments": filtered_appointments,
            }

            if args:
                result["filters_applied"] = args

            return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error listing appointments: {str(e)}"
