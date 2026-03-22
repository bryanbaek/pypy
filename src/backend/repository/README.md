Repository layer (data access)

Purpose
- DAO helpers for persistence; no business logic.
- Functions operate on open connections / transactions and return typed models.

Datastore layout
- `postgres/` — one module per table plus shared test helpers
- `schema.sql` — authoritative schema mirrored by `scripts/init-db.sql`

Notes
- There is no active Redis repository layer in the primary runtime.
