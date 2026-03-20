"""Controller layer coordinating the template document workflow."""

from typing import Protocol

from src.backend.core import normalize_document_id, prepare_document_record


class DocumentGatewayContract(Protocol):
    """Gateway contract used by document controller orchestration."""

    async def get_document(self, document_id: str) -> dict | None: ...

    async def write_document(self, document_id: str, title: str, content: str) -> dict: ...

    async def delete_document(self, document_id: str) -> None: ...


class DocumentController:
    """Application workflow service for the template document sample."""

    def __init__(self, gateway: DocumentGatewayContract) -> None:
        self._gateway = gateway

    async def write_document(self, document_id: str, title: str, content: str) -> dict:
        """Validate and persist a document with create-or-update behavior."""
        record = prepare_document_record(document_id, title, content)
        return await self._gateway.write_document(
            record.id,
            record.title,
            record.content,
        )

    async def get_document(self, document_id: str) -> dict | None:
        """Fetch a single document by id."""
        return await self._gateway.get_document(normalize_document_id(document_id))

    async def delete_document(self, document_id: str) -> dict:
        """Delete a document and return a normalized response payload."""
        normalized_document_id = normalize_document_id(document_id)
        existing = await self._gateway.get_document(normalized_document_id)
        if existing is None:
            raise ValueError("document not found")

        await self._gateway.delete_document(normalized_document_id)
        return {"deleted_id": normalized_document_id}


__all__ = ["DocumentController", "DocumentGatewayContract"]
