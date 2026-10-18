The API contract lives here (see AGENTS.md → API contract). Two files:

| File | Role |
|---|---|
| `openapi.yaml` | **The contract.** Exported from the FastAPI app with `make openapi`; never edited by hand. The clients are generated from it. It grows feature by feature: it holds only the operations the backend implements. |
| `openapi-v0.1-design.yaml` | **Design reference**, read-only. The hand-written v0.1 contract from the project design (`docs/design/project.md`). Not generated, not used by the clients. Each feature implements its part of it in the code, and that part then appears in `openapi.yaml`. |

- **Owner:** backend. The contract is code-first: backend changes the Pydantic
  models and routes, runs `make openapi` (it calls
  `uv run --directory backend python scripts/export_openapi.py`) and commits
  `openapi.yaml` together with the code that changes it.
- **Base URL:** paths are relative to the server `http://localhost:8000/api/v1`.
- **Errors:** every error response is RFC 9457 `application/problem+json`
  (`type`, `title`, `status`, optional `detail`; `errors[]` with `field` and
  `message` for validation errors).
- **Drift check:** CI exports it again and fails if the result differs from
  the committed `openapi.yaml` (also checked by `backend/tests/test_contract.py`).
- **Client:** frontend runs `npm run gen:api`, which generates the types
  (`openapi-typescript`) and the typed client (`openapi-fetch`) in
  `packages/api-client/`, used by both the web and the mobile app.
- **Breaking changes** (listed in AGENTS.md) are alignment changes and need the
  user's approval in the MR.
