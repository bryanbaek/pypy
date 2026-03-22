# FastAPI Template

This repository is a reusable Python/FastAPI template with a small document CRUD sample. The default example is intentionally domain-neutral so you can copy the layer boundaries without inheriting business-specific rules.

## Sample Layout

The template demonstrates a single document flow across the backend layers in `src/backend`:

- `src/backend/controller`: workflow orchestration plus input normalization for the sample document payload.
- `src/backend/repository`: persistence helpers for `get`, `write` (create-or-update), and `delete`.
- `src/backend/gateway`: connection-aware delegation into the repository layer.
- `src/backend/handlers`: request-payload translation plus a small sample artifact written during a successful document write.
- `src/backend/db/postgres.py`: repository-owned Postgres bootstrap helpers and the adjacent `init-db.sql` schema used for the sample tables plus durable workflow state storage.


## Sample Operations

The default sample supports three basic operations:

- `get_document(document_id)`
- `write_document(document_id, title, content)`
- `delete_document(document_id)`

`write_document` uses create-or-update semantics so the same sample covers both initial creation and later replacement.
The controller normalizes document ids and titles before delegating to the gateway and repository layers.

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

## Postgres Bootstrap

The checked-in bootstrap script lives at `src/backend/db/init-db.sql`.
It creates the sample `documents` and `appointments` tables expected by the repository layer, plus the durable workflow tables `workflow_state_store` and `workflow_state_transitions`.
The adjacent `src/backend/db/postgres.py` module points to the bootstrap asset from the Python side without wiring new runtime behavior into the template.

Apply the schema to an existing local Postgres database with:

```bash
psql "$DATABASE_URL" -f src/backend/db/init-db.sql
```

For Docker-based startup, mount the same file into the official Postgres entrypoint directory.
The current `docker-compose.yaml` only starts the FastAPI app, so add a Postgres service with a volume such as:

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: pypy
      POSTGRES_USER: pypy
      POSTGRES_PASSWORD: pypy
    volumes:
      - ./src/backend/db/init-db.sql:/docker-entrypoint-initdb.d/init-db.sql:ro
```

The official Postgres image applies files in `/docker-entrypoint-initdb.d/` only when it initializes a fresh data directory.
If you are reusing an existing local volume, rerun the `psql` command above instead.

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
- `src/backend/db/postgres.py`
- `src/backend/db/init-db.sql`
- `src/backend/controller/document_controller.py`
- `src/backend/controller/document_controller_test.py`
- `src/backend/controller/appointment_controller.py`
- `src/backend/controller/appointment_controller_test.py`
- `src/backend/repository/document_repository.py`
- `src/backend/repository/appointment_repository.py`
- `src/backend/gateway/document_gateway.py`
- `src/backend/gateway/appointment_gateway.py`
- `src/backend/handlers/document_handlers.py`
- `src/backend/handlers/appointment_handlers.py`
- `src/backend/main_test.py`

## Notes

- The sample is deliberately small and not production-ready.
- The repository still includes infrastructure scaffolding such as Docker, GitHub Actions, and FastAPI app wiring so you can build on top of the template.
