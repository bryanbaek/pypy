import asyncio

import pytest

from src.backend.core.document_workflow import (
    normalize_document_id,
    prepare_document_record,
    write_document_sample,
)
from src.backend.db.postgres import write_document


class FakeConn:
    def __init__(self):
        self.calls = []
        self.documents = {}

    async def fetchrow(self, query, *args):
        self.calls.append((query, args))
        if "INSERT INTO documents" in query and "RETURNING" in query:
            document = {"id": args[0], "title": args[1], "content": args[2]}
            self.documents[document["id"]] = document
            return document
        return None


class FakeConnNoReturn(FakeConn):
    async def fetchrow(self, query, *args):
        self.calls.append((query, args))
        if "INSERT INTO documents" in query and "RETURNING" in query:
            return None
        return await super().fetchrow(query, *args)


def test_prepare_document_record_normalizes_fields():
    record = prepare_document_record("  doc-1  ", "  Sample   Document  ", " body ")

    assert record.id == "doc-1"
    assert record.title == "Sample Document"
    assert record.content == "body"


def test_prepare_document_record_rejects_missing_identifier():
    with pytest.raises(ValueError, match="document_id must not be empty"):
        prepare_document_record("   ", "Title", "body")


def test_prepare_document_record_rejects_non_string_title():
    with pytest.raises(ValueError, match="title must be a string"):
        prepare_document_record("doc-1", 123, "body")


def test_normalize_document_id_trims_surrounding_whitespace():
    assert normalize_document_id("  doc-1  ") == "doc-1"


def test_write_document_sample_persists_normalized_record():
    conn = FakeConn()

    result = asyncio.run(
        write_document_sample(conn, "  doc-1  ", "  Sample   Document  ", " body ")
    )

    assert result.id == "doc-1"
    assert result.title == "Sample Document"
    assert result.content == "body"
    assert len(conn.calls) == 1
    assert "INSERT INTO documents" in conn.calls[0][0]
    assert conn.calls[0][1] == ("doc-1", "Sample Document", "body")


def test_write_document_sample_returns_fallback_payload_when_row_missing():
    conn = FakeConnNoReturn()

    result = asyncio.run(write_document_sample(conn, "doc-1", "Title", "Body"))

    assert result == {"id": "doc-1", "title": "Title", "content": "Body"}


def test_db_write_document_uses_core_normalization():
    conn = FakeConn()

    result = asyncio.run(write_document(conn, " doc-1 ", " Example   Title ", " text "))

    assert result.id == "doc-1"
    assert result.title == "Example Title"
    assert result.content == "text"
    assert conn.calls[0][1] == ("doc-1", "Example Title", "text")
