"""Document workflow slice with repository, gateway, controller, and handlers."""

from sandbox.document.controller import DocumentController
from sandbox.document.gateway import DocumentGateway
from sandbox.document.handlers import (
    DOCUMENT_SAMPLE_ARTIFACT_PATH,
    DOCUMENT_SAMPLE_ARTIFACT_SCENARIO,
    DOCUMENT_SAMPLE_ARTIFACT_TAG,
    handle_delete_document,
    handle_get_document,
    handle_write_document,
)

__all__ = [
    "DOCUMENT_SAMPLE_ARTIFACT_PATH",
    "DOCUMENT_SAMPLE_ARTIFACT_SCENARIO",
    "DOCUMENT_SAMPLE_ARTIFACT_TAG",
    "DocumentController",
    "DocumentGateway",
    "handle_delete_document",
    "handle_get_document",
    "handle_write_document",
]
