"""Gateway layer for the template document workflow."""

from typing import Protocol

import src.backend.repository.document_repository as default_repository
from src.backend.repository.document_repository import DocumentConnection


class DocumentRepository(Protocol):
    """Repository contract used by the document gateway."""

    async def get_document(
        self, conn: DocumentConnection, document_id: str
    ) -> dict | None: ...

    async def write_document(
        self, conn: DocumentConnection, document_id: str, title: str, content: str
    ) -> dict: ...

    async def delete_document(
        self, conn: DocumentConnection, document_id: str
    ) -> None: ...


class DocumentGateway:
    """Abstraction over repository access for document operations."""

    def __init__(
        self,
        conn: DocumentConnection,
        repository: DocumentRepository = default_repository,
    ) -> None:
        self._conn = conn
        self._repository = repository

    async def get_document(self, document_id: str) -> dict | None:
        """Get a single document by id."""
        return await self._repository.get_document(self._conn, document_id)

    async def write_document(self, document_id: str, title: str, content: str) -> dict:
        """Create or update a document through the repository."""
        return await self._repository.write_document(
            self._conn,
            document_id,
            title,
            content,
        )

    async def delete_document(self, document_id: str) -> None:
        """Delete a document by id."""
        await self._repository.delete_document(self._conn, document_id)


__all__ = ["DocumentGateway", "DocumentRepository"]
