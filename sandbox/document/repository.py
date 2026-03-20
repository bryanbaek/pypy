"""Sandbox re-export of the template document repository."""

from src.backend.repository import (
    DocumentConnection,
    delete_document,
    get_document,
    write_document,
)

__all__ = ["DocumentConnection", "delete_document", "get_document", "write_document"]
