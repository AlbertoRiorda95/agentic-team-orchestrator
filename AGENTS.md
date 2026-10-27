# Project: DevOrchestrator

DevOrchestrator (repository `agentic-team-orchestrator`) is an application for
managing a software development team made of AI agents. Tagline: "AI agents.
Real software."

## Stack
- **Backend:** Python 3.14, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async),
  Alembic migrations, PostgreSQL 17. Package manager: uv (`backend/uv.lock`).
  Tests: pytest. Lint and format: ruff. Type check: mypy.
- **Web app:** React 19 + Vite, TypeScript 5, Node 24. UI: shadcn/ui (Radix +
  Tailwind CSS v4). Tests: Vitest.
- **Mobile app:** React Native + Expo (Expo Router), TypeScript 5. UI:
  NativeWind + React Native Reusables. Tests: Jest (`jest-expo`). Release
  builds (EAS) are not set up yet: only local `expo export` checks.
- **Shared TypeScript:** npm workspaces monorepo; `packages/api-client`
  (generated from the contract), `packages/tokens` (design tokens and the
  shared Tailwind preset), `packages/shared`.
- **Containers:** Docker; `compose.yml` for local development (API +
  Postgres). Deployment target: not decided yet.
- Linters: ESLint + Prettier (TypeScript), ruff (Python).

Layout:
```
backend/              FastAPI app (backend/app/), tests (backend/tests/),
                      Alembic migrations (backend/migrations/)
apps/web/             React + Vite web app
apps/mobile/          Expo mobile app
packages/api-client/  client generated from docs/api/openapi.yaml
packages/tokens/      design tokens, shared by web and mobile
packages/shared/      shared TypeScript code
```

## Commands
The root `Makefile` is the entry point for agents, hooks and CI.
- Install: `make install` (`uv sync --directory backend` + `npm ci`)
- Build: `make build` (web bundle + `docker build -f backend/Dockerfile .`)
- Test all: `make test` (pytest + Vitest + Jest)
- Single test: `uv run --directory backend pytest <file>` (backend),
  `npx vitest run <file>` (web), `npx jest <file>` (mobile)
- Lint: `make lint` (`ruff check` + `ruff format --check` + `npm run lint`)
- Lint one file: `uv run --directory backend ruff check <file>` (`.py`),
  `npx eslint <file>` (`.ts`, `.tsx`)
- Type check: `uv run --directory backend mypy` and `npm run typecheck`
  (`tsc --noEmit` in every workspace)
- Export the API contract: `make openapi`
- Generate the API client: `npm run gen:api`
- Dev servers: API `uv run --directory backend fastapi dev` (port 8000), web
  `npm run dev -w apps/web` (port 5173), mobile `npx expo start` in
  `apps/mobile` (port 8081), Postgres `docker compose up db` (port 5432)

## How work is delegated in this project
Route by file boundary, not by topic:
<!-- agent-team:if role_frontend -->
- `apps/web/`, `apps/mobile/`, `packages/`, root `package.json`,
  `package-lock.json` and `tsconfig*.json` → frontend
<!-- agent-team:end -->
<!-- agent-team:if role_backend -->
- `backend/` (except `backend/Dockerfile`), `docs/api/openapi.yaml` → backend
<!-- agent-team:end -->
<!-- agent-team:if role_designer -->
- `docs/design/`, UI review → designer
<!-- agent-team:end -->
<!-- agent-team:if role_devops -->
- `.github/workflows/`, `ci/`, `Dockerfile*` (including `backend/Dockerfile`),
  `.dockerignore`, `compose*.yml`, `Makefile`, `deploy/`, `charts/`, `infra/` → devops
<!-- agent-team:end -->
<!-- agent-team:if role_optimizer -->
- Optimizing code that already works and is tested → optimizer
<!-- agent-team:end -->

Two agents never edit the same file in the same round. If a task crosses
a boundary, split it into two tasks with an explicit dependency.

## Standard feature sequence
When you plan or lead a feature with several roles: read
`docs/agents/workflow.md` for the order of the roles. Involve only the
roles the task actually touches.

## Leading a session
Each role is an agent of the harness you use, pointing to its prompt in
`docs/roles/`:
<!-- agent-team:if harness_claude -->
- Claude Code: `.claude/agents/` (`@backend`, `@designer`...)
<!-- agent-team:end -->

When you lead (you are not one of the roles):
- Delegate by file boundary, as above, and only to the roles the task touches.
- After every delegation, check `docs/alignment/` for entries with
  `status: open` and handle them as in "Alignment changes": designer first,
  then the affected roles, then mark the entry resolved. Ask the user only
  when designer sets `decision-needed: yes`.
- Between tasks start a fresh session. When one has grown long or changes
  phase, write a handoff note first (the handoff skill, in `.handoff/`).

## On-demand roles
These two roles are never part of the standard sequence. Delegate to them
only when the user asks explicitly.
<!-- agent-team:if role_optimizer -->
- optimizer: when the user asks for an optimization or a measurement shows
  a performance problem. Only with green tests.
<!-- agent-team:end -->
<!-- agent-team:if role_security -->
- security: when the user asks for a security assessment, typically once the
  application is complete or before a release. It reports findings; the
  owning roles fix them as separate tasks.
<!-- agent-team:end -->

## API contract
The contract between frontend and backend is `docs/api/openapi.yaml`.
- backend owns it. It is code-first: backend changes the Pydantic models and
  route signatures, runs `make openapi` (which exports the FastAPI schema to
  `docs/api/openapi.yaml`) and commits the file together with the code. CI
  exports it again and fails if it differs from the committed file.
- frontend generates its API types and client from it with
  `openapi-typescript` + `openapi-fetch` (`npm run gen:api`, output in
  `packages/api-client/`), shared by web and mobile. It never hand-writes
  response types, so a mismatch becomes a build error.
- How live updates (agent and task status pushed to the clients) are
  described is decided in the project design.
- These are breaking changes: removing or renaming a field; changing a type,
  a status code or an error shape; removing an endpoint or an enum value;
  making a request field required or adding a new required one; changing
  authentication or authorization requirements; changing the shape of an
  event. A breaking change is always an alignment change and needs the
  user's approval in the MR.
- Prefer expand-contract to a breaking change. Expand: add the new field or
  endpoint next to the old one (not breaking). Migrate: move the callers, in
  their own tasks. Contract: remove the old form in a last task, once nothing
  uses it; only this step is breaking. `main` stays green at every step.

## Alignment changes
A change is an alignment change when another role relies on what you
changed: the API contract, the data model, a shared component or design
token, a route or user flow, an environment variable or port, the
deployment interface. When you make one, read and follow
`docs/agents/alignment.md` before opening the MR. Never adapt other
roles' code yourself.

<!-- agent-team:if team_tasks -->
## Team tasks
Only when the user asks for one (`agent:team` on GitHub, `AI_FLOW_ROLES`
on GitLab, or in a local session): read `docs/agents/team-tasks.md`.

<!-- agent-team:end -->
<!-- agent-team:if split -->
## Splitting issues
When you are asked to propose how to split an issue into task issues
(`agent:split`, `SPLIT_ISSUE`): read `docs/agents/splitting.md`.

<!-- agent-team:end -->
## Specs before code
Implementation tasks start from a spec in `docs/design/` marked `ready: yes`
(see `docs/design/_spec-template.md`). The project design is
`docs/design/project.md`.
- If the task has no spec, the spec is not ready, or it does not cover what
  you are asked to do: stop, write what is missing in the issue or in your
  final message, and do not invent the missing design.
- Large design work happens in a studio session with the user
  (`docs/roles/design-studio.md`), not in MR comments. MR comments are code
  review.

## Branches and merge requests
One branch per task. Before opening or updating an MR: read
`docs/agents/merge-requests.md` (branch name, update from `main`,
description sections).

## CI
A red CI is part of your task: fix the cause, never weaken a check (no
edits to `ci/scanners.env`, skipped tests or ignore rules without the
user's approval in the MR). When a check fails, or when you touch tests,
UI screens, workflows or CI files: read `docs/agents/ci.md`.

## Rules for everyone
- Small commits, messages in English, imperative mood.
- Nobody pushes to `main`. Nobody merges. Nobody closes an issue.
- If a requirement is ambiguous, stop and ask; do not guess.
