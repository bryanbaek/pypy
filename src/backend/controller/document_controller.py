"""Controller layer coordinating the template document workflow."""

from typing import Protocol


def _normalize_required_text(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def _normalize_document_id(document_id: str) -> str:
    """Normalize and validate a document identifier."""
    return _normalize_required_text(document_id, field_name="document_id")


class DocumentGatewayContract(Protocol):
    """Gateway contract used by document controller orchestration."""

    async def get_document(self, document_id: str) -> dict | None: ...

    async def write_document(
        self, document_id: str, title: str, content: str
    ) -> dict: ...

    async def delete_document(self, document_id: str) -> None: ...


class DocumentController:
    """Application workflow service for the template document sample."""

    def __init__(self, gateway: DocumentGatewayContract) -> None:
        self._gateway = gateway

    async def write_document(
        self, document_id: str, title: str, content: str
    ) -> dict:
        """Validate and persist a document with create-or-update behavior."""
        return await self._gateway.write_document(
            _normalize_document_id(document_id),
            _normalize_required_text(title, field_name="title"),
            content,
        )

    async def get_document(self, document_id: str) -> dict | None:
        """Fetch a single document by id."""
        return await self._gateway.get_document(_normalize_document_id(document_id))

    async def delete_document(self, document_id: str) -> dict:
        """Delete a document and return a normalized response payload."""
        normalized_document_id = _normalize_document_id(document_id)
        existing = await self._gateway.get_document(normalized_document_id)
        if existing is None:
            raise ValueError("document not found")

        await self._gateway.delete_document(normalized_document_id)
        return {"deleted_id": normalized_document_id}


__all__ = ["DocumentController", "DocumentGatewayContract"]
