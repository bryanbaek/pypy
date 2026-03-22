# FastAPI Template

This repository is a reusable Python/FastAPI template with a small document CRUD sample. The default example is intentionally domain-neutral so you can copy the layer boundaries without inheriting business-specific rules. A minimal Bun + Vite + TypeScript frontend starter also lives alongside the backend so the template includes a simple browser-facing demo surface.

## Sample Layout

The template includes a lightweight frontend starter in `src/frontend` plus the existing sample workflows in `src/backend`:

- `src/frontend`: Bun + Vite + TypeScript demo page for browser-facing starter work.
- `src/backend/controller`: workflow orchestration plus input normalization for the sample document payload.
- `src/backend/repository`: canonical Postgres read/write helpers for the sample document and appointment CRUD flows.
- `src/backend/gateway`: connection-aware delegation into the repository package rather than issuing SQL directly.
- `src/backend/handlers`: request-payload translation plus a small sample artifact written during a successful document write.
- `src/backend/db/postgres.py`: repository-owned Postgres bootstrap helpers and the adjacent `init-db.sql` schema used for the sample tables plus durable workflow state storage.


## Sample Operations

The default sample supports three basic operations:

- `get_document(document_id)`
- `write_document(document_id, title, content)`
- `delete_document(document_id)`

`write_document` uses create-or-update semantics so the same sample covers both initial creation and later replacement.
The controller normalizes document ids and titles before delegating to the gateway and repository layers, and the same layering applies to the sample appointment flow.

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

Then open `http://localhost:5173` in a browser. The demo page links to the FastAPI sample using `VITE_BACKEND_URL`, which defaults to `http://localhost:8000` for local development.

Create a production build with:

```bash
cd src/frontend
bun run build
```

The built assets are written to `src/frontend/dist/`.

### Docker Compose

For the full local stack, copy `env.example` to `.env`, adjust any ports or database credentials you need, and then start the services:

```bash
cp env.example .env
docker compose up --build
```

By default, the compose stack exposes:

- FastAPI on `http://localhost:8000`
- Bun/Vite frontend on `http://localhost:5173`
- Postgres on `localhost:5432`

`docker-compose.yaml` reads its local database and app settings from the variables you copied from `env.example` into `.env`, including `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `BACKEND_PORT`, `FRONTEND_PORT`, and `VITE_BACKEND_URL`.
The frontend service runs the existing app in `src/frontend`, the backend service continues to run `src.backend.main:app`, and the Postgres service mounts the bootstrap SQL from `src/backend/db/init-db.sql`.
If you change the published backend URL, update `VITE_BACKEND_URL` so the frontend demo links still point at the FastAPI service.

The Postgres data directory lives in the named `postgres-data` volume.
That means `docker compose stop`, `docker compose start`, and `docker compose down` preserve your sample document data, appointment data, and workflow state.
Run `docker compose down -v` only when you want to remove the named volume and force Postgres to initialize a fresh database on the next `docker compose up`.

## Postgres Bootstrap

The checked-in bootstrap script lives at `src/backend/db/init-db.sql`.
It creates the sample `documents` and `appointments` tables expected by the repository layer, plus the durable workflow tables `workflow_state_store` and `workflow_state_transitions`.
All workflow-specific Postgres CRUD reads and writes live in `src/backend/repository/document_repository.py` and `src/backend/repository/appointment_repository.py`.
The adjacent `src/backend/db/postgres.py` module only points to the bootstrap asset from the Python side without owning sample-specific DAO behavior.

When you start the compose stack, `docker-compose.yaml` mounts that same SQL file into the official Postgres entrypoint directory at `/docker-entrypoint-initdb.d/init-db.sql`.
The official Postgres image applies files from that directory only when it initializes a fresh data directory, so the named `postgres-data` volume preserves both schema and data across container recreation.
If you need the bootstrap script to run again after changing the schema, remove the volume with `docker compose down -v` before starting the stack again.

Apply the schema to an existing local Postgres database with:

```bash
psql "$DATABASE_URL" -f src/backend/db/init-db.sql
```

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
- `src/backend/repository/__init__.py`
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
