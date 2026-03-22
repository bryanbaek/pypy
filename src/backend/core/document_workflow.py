"""Core normalization helpers for the template document workflow."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DocumentRecord:
    """Normalized document payload used by document controller orchestration."""

    id: str
    title: str
    content: str


def _normalize_required_text(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def normalize_document_id(document_id: str) -> str:
    """Normalize and validate a document identifier."""
    return _normalize_required_text(document_id, field_name="document_id")


def prepare_document_record(
    document_id: str,
    title: str,
    content: str,
) -> DocumentRecord:
    """Normalize a document payload before it reaches the repository layer."""
    return DocumentRecord(
        id=normalize_document_id(document_id),
        title=_normalize_required_text(title, field_name="title"),
        content=content,
    )


__all__ = ["DocumentRecord", "normalize_document_id", "prepare_document_record"]
