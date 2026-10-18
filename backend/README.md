# DevOrchestrator API

FastAPI app (`app/`), tests (`tests/`), Alembic migrations (`migrations/`).
Package manager: uv. Commands run from the repository root:

| What | Command |
|---|---|
| Install | `uv sync --directory backend` |
| Dev server (port 8000) | `uv run --directory backend fastapi dev` |
| Tests | `uv run --directory backend pytest` |
| Lint, format | `uv run --directory backend ruff check .`, `uv run --directory backend ruff format --check .` |
| Type check | `uv run --directory backend mypy` |
| Migrations | `uv run --directory backend alembic upgrade head` |
| Export the API contract | `uv run --directory backend python scripts/export_openapi.py` (writes `docs/api/openapi.yaml`) |

## Configuration
Environment variables only (no defaults for credentials in the code):

| Variable | Meaning |
|---|---|
| `DATABASE_URL` | required at startup, e.g. `postgresql+asyncpg://user:password@host:5432/db` |
| `CORS_ORIGINS` | comma separated origins allowed by CORS; default `http://localhost:8081` |
| `GIT_SHA` | optional; adds `+<short sha>` to the version reported by `/health` |

The API is served under `/api/v1` (`/api/v1/docs` for the interactive docs).
Database-backed tests run when `DATABASE_URL` is set and are skipped otherwise.
