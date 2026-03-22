Gateway layer (outbound integrations)

Purpose
- Encapsulate all calls to third-party services so controllers stay deterministic and testable.
- Provide small, typed facades that can be mocked in unit tests.

Current integrations
- `llm_gateway.py` — abstract interface and OpenAI-backed implementation for structured LLM completions (`structured_completion`) returning Pydantic models. The OpenAI gateway enforces strict JSON output using the supplied Pydantic schema and fails closed on validation errors; no raw text parsing.


OpenAI gateway configuration
- `OPENAI_API_KEY` (required)
- `OPENAI_MODEL` (required)
- `OPENAI_BASE_URL` (optional; for compatible endpoints)
- `OPENAI_TIMEOUT_S` (default `30`)
- `OPENAI_MAX_RETRIES` (default `2`)


Guidelines
- Keep APIs minimal and explicit; no global clients.
- Return structured results or raise domain-specific exceptions; avoid leaking provider-specific objects upward.
- Make timeouts/configuration injectable; prefer dependency injection in controllers/services.
- Ensure gateways are side-effect focused only (no business logic).
