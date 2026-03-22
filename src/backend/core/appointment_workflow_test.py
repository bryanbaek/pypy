"""Tests for appointment workflow validation helpers."""

from datetime import datetime

import pytest

from src.backend.core.appointment_workflow import prepare_appointment_record


def test_prepare_appointment_record_normalizes_title() -> None:
    start_time = datetime(2026, 3, 21, 9, 0, 0)
    end_time = datetime(2026, 3, 21, 10, 0, 0)

    record = prepare_appointment_record("  Weekly sync  ", start_time, end_time)

    assert record.title == "Weekly sync"
    assert record.start_time == start_time
    assert record.end_time == end_time


def test_prepare_appointment_record_rejects_blank_titles() -> None:
    start_time = datetime(2026, 3, 21, 9, 0, 0)
    end_time = datetime(2026, 3, 21, 10, 0, 0)

    with pytest.raises(ValueError, match="title must not be empty"):
        prepare_appointment_record("   ", start_time, end_time)


def test_prepare_appointment_record_rejects_invalid_ranges() -> None:
    start_time = datetime(2026, 3, 21, 10, 0, 0)
    end_time = datetime(2026, 3, 21, 9, 0, 0)

    with pytest.raises(ValueError, match="end_time must be after start_time"):
        prepare_appointment_record("Weekly sync", start_time, end_time)
