"""Tests for document controller workflow normalization."""

import asyncio

import pytest

from src.backend.controller.document_controller import DocumentController


class StubDocumentGateway:
    def __init__(self) -> None:
        self.documents: dict[str, dict] = {}
        self.deleted_ids: list[str] = []
        self.requested_ids: list[str] = []
        self.written: tuple[str, str, str] | None = None

    async def get_document(self, document_id: str) -> dict | None:
        self.requested_ids.append(document_id)
        return self.documents.get(document_id)

    async def write_document(self, document_id: str, title: str, content: str) -> dict:
        self.written = (document_id, title, content)
        document = {"id": document_id, "title": title, "content": content}
        self.documents[document_id] = document
        return document

    async def delete_document(self, document_id: str) -> None:
        self.deleted_ids.append(document_id)
        self.documents.pop(document_id, None)


def test_write_document_normalizes_required_fields() -> None:
    gateway = StubDocumentGateway()
    controller = DocumentController(gateway)

    document = asyncio.run(
        controller.write_document("  doc-123  ", "  Example Title  ", " body ")
    )

    assert gateway.written == ("doc-123", "Example Title", " body ")
    assert document == {"id": "doc-123", "title": "Example Title", "content": " body "}


@pytest.mark.parametrize(
    ("document_id", "title", "error"),
    [
        ("   ", "Example Title", "document_id must not be empty"),
        ("doc-123", "   ", "title must not be empty"),
    ],
)
def test_write_document_rejects_blank_required_fields(
    document_id: str,
    title: str,
    error: str,
) -> None:
    controller = DocumentController(StubDocumentGateway())

    with pytest.raises(ValueError, match=error):
        asyncio.run(controller.write_document(document_id, title, "body"))


def test_get_document_normalizes_document_id() -> None:
    gateway = StubDocumentGateway()
    gateway.documents["doc-123"] = {
        "id": "doc-123",
        "title": "Example Title",
        "content": "body",
    }
    controller = DocumentController(gateway)

    document = asyncio.run(controller.get_document("  doc-123  "))

    assert gateway.requested_ids == ["doc-123"]
    assert document == gateway.documents["doc-123"]


def test_delete_document_returns_normalized_response() -> None:
    gateway = StubDocumentGateway()
    gateway.documents["doc-123"] = {
        "id": "doc-123",
        "title": "Example Title",
        "content": "body",
    }
    controller = DocumentController(gateway)

    deletion = asyncio.run(controller.delete_document("  doc-123  "))

    assert gateway.requested_ids == ["doc-123"]
    assert gateway.deleted_ids == ["doc-123"]
    assert deletion == {"deleted_id": "doc-123"}
