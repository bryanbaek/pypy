import asyncio
from pathlib import Path

from sandbox.document import handlers as document_handlers
from sandbox.document.controller import DocumentController
from sandbox.document.gateway import DocumentGateway
from sandbox.document.handlers import (
    handle_delete_document,
    handle_get_document,
    handle_write_document,
)
from sandbox.document.repository import delete_document, get_document, write_document


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


def test_sandbox_repository_roundtrip():
    conn = FakeConn()

    created = asyncio.run(write_document(conn, "doc-1", "Title", "Body"))
    fetched = asyncio.run(get_document(conn, "doc-1"))

    assert created == {"id": "doc-1", "title": "Title", "content": "Body"}
    assert fetched == created

    asyncio.run(delete_document(conn, "doc-1"))
    assert asyncio.run(get_document(conn, "doc-1")) is None


def test_sandbox_handlers_integration_and_artifact(tmp_path, monkeypatch):
    artifact_path = tmp_path / "sandbox-document-crud-template.md"
    monkeypatch.setattr(document_handlers, "DOCUMENT_SAMPLE_ARTIFACT_PATH", artifact_path)

    conn = FakeConn()
    gateway = DocumentGateway(conn)
    controller = DocumentController(gateway)

    created = asyncio.run(
        handle_write_document(
            controller,
            {"id": "doc-1", "title": "  Sandbox   Title ", "content": " body "},
        )
    )
    assert created == {
        "status": "ok",
        "document": {"id": "doc-1", "title": "Sandbox Title", "content": "body"},
    }

    fetched = asyncio.run(handle_get_document(controller, "doc-1"))
    assert fetched["status"] == "ok"
    assert fetched["document"]["id"] == "doc-1"

    deleted = asyncio.run(handle_delete_document(controller, "doc-1"))
    assert deleted == {"status": "ok", "deleted_id": "doc-1"}

    assert artifact_path.exists()
    artifact_content = artifact_path.read_text(encoding="utf-8")
    assert "tag: sandbox-document-crud-template" in artifact_content
    assert "scenario: write-document" in artifact_content


def test_sandbox_handler_returns_error_for_invalid_get_identifier():
    controller = DocumentController(DocumentGateway(FakeConn()))

    result = asyncio.run(handle_get_document(controller, "   "))

    assert result == {"status": "error", "error": "document_id must not be empty"}


def test_sandbox_document_sample_artifact_exists():
    artifact_path = (
        Path(__file__).resolve().parents[1]
        / "sandbox"
        / "document"
        / "e2e"
        / "sandbox-document-crud-template.md"
    )

    assert artifact_path.exists()
    artifact_content = artifact_path.read_text(encoding="utf-8")
    assert "tag: sandbox-document-crud-template" in artifact_content
    assert "scenario: write-document" in artifact_content
