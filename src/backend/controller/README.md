Controller layer (workflow orchestration)

Purpose
- Normalize input and enforce workflow rules before touching I/O.
- Keep controllers reusable and deterministic by delegating external work to collaborators.

Starter surfaces in this template
- `document_controller.py` — sample document CRUD orchestration that shows required-field normalization and create-or-update behavior.
- `appointment_controller.py` — sample appointment orchestration that shows validation and conflict checks.
- Both files are starter examples. Keep the controller boundary, but replace the document and appointment rules when you adapt the template to a real product.
