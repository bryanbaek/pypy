Handlers layer (request/response translation)

Purpose
- Keep the HTTP or transport-facing layer thin: parse requests, call controllers, and shape responses.
- Avoid business logic and direct database mutations in handlers.

Starter surfaces in this template
- `document_handlers.py` — sample document CRUD payload translation plus a starter artifact write on successful document updates.
- `appointment_handlers.py` — sample appointment payload parsing and response shaping.
- These files are starter examples. They are not mounted by default in `src/backend/main.py`, so you can replace them with product-specific routes without first unwinding live runtime wiring.
