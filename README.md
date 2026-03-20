# FastAPI Template

This repository is a reusable Python/FastAPI template with a small document CRUD sample. The default example is intentionally domain-neutral so you can copy the layer boundaries without inheriting business-specific rules.

## Sample Layout

The template demonstrates a single document flow across the backend layers in `src/backend`:

- `src/backend/core`: input normalization for the sample document payload.
- `src/backend/repository`: persistence helpers for `get`, `write` (create-or-update), and `delete`.
- `src/backend/gateway`: connection-aware delegation into the repository layer.
- `src/backend/controller`: workflow orchestration that applies core normalization before writes.
- `src/backend/handlers`: request-payload translation plus a small sample artifact written during a successful document write.
- `src/backend/db/postgres.py`: minimal database wrapper helpers for the same document sample.

The sandbox mirror in `sandbox/document` gives contributors a generic example slice to copy or adapt without referencing any business domain.

## Sample Operations

The default sample supports three basic operations:

- `get_document(document_id)`
- `write_document(document_id, title, content)`
- `delete_document(document_id)`

`write_document` uses create-or-update semantics so the same sample covers both initial creation and later replacement.

## Run

Install dependencies with your preferred toolchain. If you use `uv`:

```bash
uv sync
uv run uvicorn src.backend.web.rest.main:app --reload
```

The included FastAPI app starts from `src/backend/web/rest/main.py`.

## Verify

The default sample is exercised by the repository test suite:

```bash
uv run pytest
```

The main files to inspect while adapting the template are:

- `src/backend/core/__init__.py`
- `src/backend/controller/__init__.py`
- `src/backend/repository/__init__.py`
- `src/backend/gateway/__init__.py`
- `src/backend/handlers/__init__.py`
- `sandbox/document/__init__.py`
- `tests/test_core_document_workflow.py`
- `tests/test_backend_document_workflow.py`
- `tests/test_sandbox_document_workflow.py`

## Notes

- The sample is deliberately small and not production-ready.
- The repository still includes infrastructure scaffolding such as Docker, GitHub Actions, and FastAPI app wiring so you can build on top of the template.
