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
uv run uvicorn src.backend.main:app --reload
```

To run the same application in Docker:

```bash
docker compose up --build
```

The included FastAPI app starts from `src/backend/main.py`.

## Verify

After syncing dependencies, run the repository verification commands from the repo root:

```bash
just lint
just test
```

`just lint` runs `uv run ruff check .` followed by `uv run ty check`.
`just test` runs `uv run pytest`, which includes colocated `*_test.py` modules under `src/`.

## Development

For repo checks during development, use `just lint` and `just test` after `uv sync`.

The main files to inspect while adapting the template are:

- `src/backend/main.py`
- `src/backend/core/document_workflow.py`
- `src/backend/core/appointment_workflow.py`
- `src/backend/controller/document_controller.py`
- `src/backend/controller/appointment_controller.py`
- `src/backend/repository/document_repository.py`
- `src/backend/repository/appointment_repository.py`
- `src/backend/gateway/document_gateway.py`
- `src/backend/gateway/appointment_gateway.py`
- `src/backend/handlers/document_handlers.py`
- `src/backend/handlers/appointment_handlers.py`
- `src/backend/main_test.py`
- `src/backend/core/document_workflow_test.py`
- `src/backend/core/appointment_workflow_test.py`

## Notes

- The sample is deliberately small and not production-ready.
- The repository still includes infrastructure scaffolding such as Docker, GitHub Actions, and FastAPI app wiring so you can build on top of the template.
