The API contract lives here: `openapi.yaml` (see AGENTS.md → API contract).

- **Owner:** backend. The contract is code-first: it is exported from the
  FastAPI app with `make openapi` and committed together with the code that
  changes it.
- **Drift check:** CI exports it again and fails if the result differs from
  the committed `openapi.yaml`.
- **Client:** frontend runs `npm run gen:api`, which generates the types
  (`openapi-typescript`) and the typed client (`openapi-fetch`) in
  `packages/api-client/`, used by both the web and the mobile app.
- **Breaking changes** (listed in AGENTS.md) are alignment changes and need the
  user's approval in the MR.
