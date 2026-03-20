"""Sandbox handler layer for the template document sample."""

from pathlib import Path
from typing import Protocol

DOCUMENT_SAMPLE_ARTIFACT_TAG = "sandbox-document-crud-template"
DOCUMENT_SAMPLE_ARTIFACT_SCENARIO = "write-document"
DOCUMENT_SAMPLE_ARTIFACT_PATH = Path(__file__).resolve().parent / "e2e" / (
    f"{DOCUMENT_SAMPLE_ARTIFACT_TAG}.md"
)


class DocumentControllerContract(Protocol):
    """Controller contract used by sandbox document handlers."""

    async def get_document(self, document_id: str) -> dict | None: ...

    async def write_document(self, document_id: str, title: str, content: str) -> dict: ...

    async def delete_document(self, document_id: str) -> dict: ...


def _write_document_sample_artifact() -> None:
    DOCUMENT_SAMPLE_ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOCUMENT_SAMPLE_ARTIFACT_PATH.write_text(
        (
            "# Sandbox Document CRUD Sample Artifact\n\n"
            f"tag: {DOCUMENT_SAMPLE_ARTIFACT_TAG}\n"
            f"scenario: {DOCUMENT_SAMPLE_ARTIFACT_SCENARIO}\n"
        ),
        encoding="utf-8",
    )


async def handle_write_document(
    controller: DocumentControllerContract, payload: dict
) -> dict:
    try:
        document = await controller.write_document(
            document_id=payload["id"],
            title=payload["title"],
            content=payload["content"],
        )
    except (KeyError, ValueError) as exc:
        return {"status": "error", "error": str(exc)}

    _write_document_sample_artifact()
    return {"status": "ok", "document": document}


async def handle_get_document(
    controller: DocumentControllerContract, document_id: str
) -> dict:
    document = await controller.get_document(document_id)
    if document is None:
        return {"status": "error", "error": "document not found"}
    return {"status": "ok", "document": document}


async def handle_delete_document(
    controller: DocumentControllerContract, document_id: str
) -> dict:
    try:
        deletion = await controller.delete_document(document_id)
    except ValueError as exc:
        return {"status": "error", "error": str(exc)}
    return {"status": "ok", **deletion}


__all__ = [
    "DOCUMENT_SAMPLE_ARTIFACT_PATH",
    "DOCUMENT_SAMPLE_ARTIFACT_SCENARIO",
    "DOCUMENT_SAMPLE_ARTIFACT_TAG",
    "handle_delete_document",
    "handle_get_document",
    "handle_write_document",
]
