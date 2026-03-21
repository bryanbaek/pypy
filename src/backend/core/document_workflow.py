"""Core helpers for the template document CRUD sample."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class DocumentRecord:
    """Normalized document payload used across the sample layers."""

    id: str
    title: str
    content: str


class DocumentWriteConnection(Protocol):
    """Minimal async database interface required by core write helpers."""

    async def fetchrow(self, query: str, *args: object) -> dict | None: ...


def _normalize_required_text(field: str, value: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field} must not be empty")
    return normalized


def prepare_document_record(
    document_id: str, title: str, content: str
) -> DocumentRecord:
    """Normalize the sample document payload before persistence."""
    return DocumentRecord(
        id=_normalize_required_text("document_id", document_id),
        title=_normalize_required_text("title", " ".join(title.split())),
        content=_normalize_required_text("content", content),
    )


def normalize_document_id(document_id: str) -> str:
    """Normalize a document identifier for non-write document operations."""
    return _normalize_required_text("document_id", document_id)


def _record_to_dict(record: DocumentRecord) -> dict:
    return {"id": record.id, "title": record.title, "content": record.content}


async def write_document_sample(
    conn: DocumentWriteConnection, document_id: str, title: str, content: str
) -> DocumentRecord | dict:
    """Normalize and write the template document sample with create-or-update behavior."""
    record = prepare_document_record(document_id, title, content)
    row = await conn.fetchrow(
        """
        INSERT INTO documents (id, title, content)
        VALUES ($1, $2, $3)
        ON CONFLICT (id)
        DO UPDATE SET title = EXCLUDED.title, content = EXCLUDED.content
        RETURNING id, title, content
        """,
        record.id,
        record.title,
        record.content,
    )
    if row is None:
        return _record_to_dict(record)
    return DocumentRecord(id=row["id"], title=row["title"], content=row["content"])


__all__ = [
    "DocumentRecord",
    "DocumentWriteConnection",
    "normalize_document_id",
    "prepare_document_record",
    "write_document_sample",
]
