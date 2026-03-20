import asyncio

import pytest

from src.backend import handlers as document_handlers
from src.backend.controller import DocumentController
from src.backend.gateway import DocumentGateway
from src.backend.handlers import (
    handle_delete_document,
    handle_get_document,
    handle_write_document,
)
from src.backend.repository import delete_document, get_document, write_document


class FakeConn:
    def __init__(self):
        self.calls = []
        self.documents = {}

    async def execute(self, query, *args):
        self.calls.append((query, args))
        if "DELETE FROM documents" in query:
            self.documents.pop(args[0], None)

    async def fetchrow(self, query, *args):
        self.calls.append((query, args))

        if "INSERT INTO documents" in query and "RETURNING" in query:
            document = {"id": args[0], "title": args[1], "content": args[2]}
            self.documents[document["id"]] = document
            return document

        if "SELECT id, title, content" in query:
            return self.documents.get(args[0])

        return None


class FakeConnNoReturn(FakeConn):
    async def fetchrow(self, query, *args):
        self.calls.append((query, args))
        if "INSERT INTO documents" in query and "RETURNING" in query:
            return None
        return await super().fetchrow(query, *args)


class FakeRepository:
    def __init__(self):
        self.calls = []

    async def get_document(self, conn, document_id):
        self.calls.append(("get_document", conn, document_id))
        return {"id": document_id, "title": "Title", "content": "Body"}

    async def write_document(self, conn, document_id, title, content):
        self.calls.append(("write_document", conn, document_id, title, content))
        return {"id": document_id, "title": title, "content": content}

    async def delete_document(self, conn, document_id):
        self.calls.append(("delete_document", conn, document_id))


class FakeGateway:
    def __init__(self):
        self.calls = []
        self.documents = {"doc-1": {"id": "doc-1", "title": "Initial", "content": "Body"}}

    async def get_document(self, document_id):
        self.calls.append(("get_document", document_id))
        return self.documents.get(document_id)

    async def write_document(self, document_id, title, content):
        self.calls.append(("write_document", document_id, title, content))
        document = {"id": document_id, "title": title, "content": content}
        self.documents[document_id] = document
        return document

    async def delete_document(self, document_id):
        self.calls.append(("delete_document", document_id))
        self.documents.pop(document_id, None)


def test_repository_document_roundtrip():
    conn = FakeConn()

    created = asyncio.run(write_document(conn, "doc-1", "Title", "Body"))
    fetched = asyncio.run(get_document(conn, "doc-1"))

    assert created == {"id": "doc-1", "title": "Title", "content": "Body"}
    assert fetched == created

    asyncio.run(delete_document(conn, "doc-1"))
    assert asyncio.run(get_document(conn, "doc-1")) is None


def test_repository_write_returns_fallback_payload_when_row_missing():
    conn = FakeConnNoReturn()

    created = asyncio.run(write_document(conn, "doc-1", "Title", "Body"))

    assert created == {"id": "doc-1", "title": "Title", "content": "Body"}


def test_gateway_delegates_to_repository_with_connection_context():
    conn = object()
    repository = FakeRepository()
    gateway = DocumentGateway(conn, repository=repository)

    fetched = asyncio.run(gateway.get_document("doc-1"))
    written = asyncio.run(gateway.write_document("doc-1", "Title", "Body"))
    asyncio.run(gateway.delete_document("doc-1"))

    assert fetched == {"id": "doc-1", "title": "Title", "content": "Body"}
    assert written == {"id": "doc-1", "title": "Title", "content": "Body"}
    assert repository.calls == [
        ("get_document", conn, "doc-1"),
        ("write_document", conn, "doc-1", "Title", "Body"),
        ("delete_document", conn, "doc-1"),
    ]


def test_controller_normalizes_before_write():
    gateway = FakeGateway()
    controller = DocumentController(gateway)

    result = asyncio.run(
        controller.write_document("  doc-1  ", "  Example   Title  ", " body ")
    )

    assert result == {"id": "doc-1", "title": "Example Title", "content": "body"}
    assert gateway.calls == [("write_document", "doc-1", "Example Title", "body")]


def test_controller_normalizes_identifier_before_get():
    gateway = FakeGateway()
    controller = DocumentController(gateway)

    result = asyncio.run(controller.get_document("  doc-1  "))

    assert result == {"id": "doc-1", "title": "Initial", "content": "Body"}
    assert gateway.calls == [("get_document", "doc-1")]


def test_controller_delete_rejects_missing_document():
    gateway = FakeGateway()
    gateway.documents = {}
    controller = DocumentController(gateway)

    with pytest.raises(ValueError, match="document not found"):
        asyncio.run(controller.delete_document("doc-1"))

    assert gateway.calls == [("get_document", "doc-1")]


def test_controller_normalizes_identifier_before_delete():
    gateway = FakeGateway()
    controller = DocumentController(gateway)

    result = asyncio.run(controller.delete_document("  doc-1  "))

    assert result == {"deleted_id": "doc-1"}
    assert gateway.calls == [("get_document", "doc-1"), ("delete_document", "doc-1")]


def test_handler_returns_error_for_missing_write_field():
    controller = DocumentController(FakeGateway())

    result = asyncio.run(
        handle_write_document(
            controller,
            {"id": "doc-1", "title": "Title"},
        )
    )

    assert result == {"status": "error", "error": "'content'"}


def test_handler_returns_error_for_invalid_get_identifier():
    controller = DocumentController(FakeGateway())

    result = asyncio.run(handle_get_document(controller, "   "))

    assert result == {"status": "error", "error": "document_id must not be empty"}


def test_handler_controller_gateway_repository_integration():
    conn = FakeConn()
    gateway = DocumentGateway(conn)
    controller = DocumentController(gateway)

    created = asyncio.run(
        handle_write_document(
            controller,
            {"id": " doc-1 ", "title": "  Example   Title  ", "content": " body "},
        )
    )
    assert created == {
        "status": "ok",
        "document": {"id": "doc-1", "title": "Example Title", "content": "body"},
    }

    fetched = asyncio.run(handle_get_document(controller, "doc-1"))
    assert fetched == {
        "status": "ok",
        "document": {"id": "doc-1", "title": "Example Title", "content": "body"},
    }

    deleted = asyncio.run(handle_delete_document(controller, "doc-1"))
    assert deleted == {"status": "ok", "deleted_id": "doc-1"}

    missing = asyncio.run(handle_get_document(controller, "doc-1"))
    assert missing == {"status": "error", "error": "document not found"}


def test_handler_writes_document_sample_artifact(tmp_path, monkeypatch):
    artifact_path = tmp_path / "document-crud-template.md"
    monkeypatch.setattr(document_handlers, "DOCUMENT_SAMPLE_ARTIFACT_PATH", artifact_path)

    controller = DocumentController(FakeGateway())
    created = asyncio.run(
        handle_write_document(
            controller,
            {"id": "doc-1", "title": "Title", "content": "Body"},
        )
    )

    assert created["status"] == "ok"
    assert artifact_path.exists()
    artifact_content = artifact_path.read_text(encoding="utf-8")
    assert "tag: document-crud-template" in artifact_content
    assert "scenario: write-document" in artifact_content


def test_document_sample_artifact_exists_with_expected_tag_and_scenario():
    artifact_path = document_handlers.DOCUMENT_SAMPLE_ARTIFACT_PATH

    assert artifact_path.exists()
    artifact_content = artifact_path.read_text(encoding="utf-8")
    assert f"tag: {document_handlers.DOCUMENT_SAMPLE_ARTIFACT_TAG}" in artifact_content
    assert (
        f"scenario: {document_handlers.DOCUMENT_SAMPLE_ARTIFACT_SCENARIO}"
        in artifact_content
    )
