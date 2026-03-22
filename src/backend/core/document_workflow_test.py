"""Tests for document workflow normalization helpers."""

import pytest

from src.backend.core.document_workflow import (
    normalize_document_id,
    prepare_document_record,
)


def test_normalize_document_id_strips_whitespace() -> None:
    assert normalize_document_id("  doc-123  ") == "doc-123"


def test_normalize_document_id_rejects_blank_values() -> None:
    with pytest.raises(ValueError, match="document_id must not be empty"):
        normalize_document_id("   ")


def test_prepare_document_record_normalizes_required_fields() -> None:
    record = prepare_document_record("  doc-123  ", "  Example Title  ", " body ")

    assert record.id == "doc-123"
    assert record.title == "Example Title"
    assert record.content == " body "
