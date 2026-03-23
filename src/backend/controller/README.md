Controller layer (workflow orchestration)

Purpose
- Normalize input and enforce workflow rules before touching I/O.
- Keep controllers reusable and deterministic by delegating external work to collaborators.

Starter surfaces in this template
- `job_controller.py` — sample workflow job orchestration that shows identifier normalization, typed detail retrieval, and explicit resume rules.
- Keep the controller boundary, but replace the sample document, appointment, and job rules when you adapt the template to a real product.
