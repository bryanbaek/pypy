# FastAPI Template

This repository is a reusable Python/FastAPI template with a small document CRUD sample. The default example is intentionally domain-neutral so you can copy the layer boundaries without inheriting business-specific rules. A minimal Bun + Vite + TypeScript frontend starter also lives alongside the backend so the template includes a simple browser-facing demo surface.

## Sample Layout

The template includes a lightweight frontend starter in `src/frontend` plus the existing document flow in `src/backend`:

- `src/frontend`: Bun + Vite + TypeScript demo page for browser-facing starter work.
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

## Frontend Demo

The frontend sample lives in `src/frontend`. It is intentionally lightweight and domain-neutral: a single Bun + Vite + TypeScript page that gives contributors a concrete place to start UI work without replacing the existing FastAPI document workflow.

## Run

### Backend

Install backend dependencies with your preferred Python toolchain. If you use `uv`:

```bash
uv sync
uv run uvicorn src.backend.main:app --reload
```

The included FastAPI app starts from `src/backend/main.py`.

To run the same backend application in Docker:

```bash
docker compose up --build
```

### Frontend

The frontend starter uses Bun as its package manager/runtime. After installing Bun locally, install frontend dependencies from the repo root:

```bash
cd src/frontend
bun install
```

Start the Vite development server:

```bash
cd src/frontend
bun run dev
```

Then open `http://localhost:5173` in a browser. The demo page includes quick links to the FastAPI sample on `http://localhost:8000`, but the frontend starter runs as a separate dev server so it does not change the backend document example.

Create a production build with:

```bash
cd src/frontend
bun run build
```

The built assets are written to `src/frontend/dist/`.

The checked-in `Dockerfile` and `docker-compose.yaml` continue to target the FastAPI app only; the frontend demo is intentionally a local Bun/Vite workflow.

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
Pull requests to `main` and pushes to `main` run the same lint and test commands in GitHub Actions.

## Development

For repo checks during development, use `just lint` and `just test` after `uv sync`.

The main files to inspect while adapting the template are:

- `src/frontend/package.json`
- `src/frontend/index.html`
- `src/frontend/src/main.ts`
- `src/frontend/src/style.css`
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
