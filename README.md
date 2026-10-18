# DevOrchestrator

**AI agents. Real software.**

DevOrchestrator (repository `agentic-team-orchestrator`) is an application for
managing a software development team made of AI agents. It has a web app, a mobile
app and an API. The project itself is built by a team of Claude agents (designer,
frontend, backend, devops, plus optimizer and security on request), configured in
this repository.

## Stack

| Part | Technology |
|---|---|
| API | Python 3.14, FastAPI, Pydantic v2, SQLAlchemy 2.0 (async), Alembic, PostgreSQL 17, uv |
| Web | React 19, Vite, TypeScript 5, Node 24, shadcn/ui + Tailwind CSS v4 |
| Mobile | React Native + Expo (Expo Router), NativeWind + React Native Reusables |
| Shared | npm workspaces: generated API client, design tokens, shared code |
| Containers | Docker, `compose.yml` for local development; deployment not decided yet |

## Layout

```
backend/                FastAPI app, tests, Alembic migrations
apps/web/               React web app
apps/mobile/            Expo mobile app
packages/api-client/    client generated from docs/api/openapi.yaml
packages/tokens/        design tokens and the shared Tailwind preset
packages/shared/        shared TypeScript code
docs/design/            project design (project.md), one spec per feature, brand assets
docs/api/               API contract (openapi.yaml), owned by backend
docs/alignment/         one entry per change that other roles rely on
docs/roles/             the agents' role prompts
docs/security/          security assessments (ignored by Git)
.claude/                agents, hooks, skills and permissions for Claude Code
.github/workflows/      ci.yml (build, test, SBOM, licenses, vulnerabilities) and the agent workflows
ci/                     CI security steps: syft, grype, trivy
```

The application folders are created by the first roadmap tasks.

## Commands

```bash
make install                              # uv sync (backend) + npm ci
make lint && make test                    # ruff, ESLint; pytest, Vitest, Jest
make build                                # web bundle + API image
make openapi                              # export the API contract from FastAPI
npm run gen:api                           # regenerate the typed client

docker compose up db                      # Postgres on 5432
uv run --directory backend fastapi dev    # API on 8000
npm run dev -w apps/web                   # web on 5173
cd apps/mobile && npx expo start          # mobile (Metro on 8081)
```

## How the agent team works

- **Specs first.** Every feature starts with a design studio session
  (`/design-studio <feature>`) that produces `docs/design/<feature>.md` with
  `ready: yes`. Agents implement only what a ready spec says.
- **Locally:** run `claude` and ask for the work; the lead delegates by folder
  (`AGENTS.md` → How work is delegated).
- **On GitHub:** open an issue from the "Agent task" template and add a label:
  `agent:designer`, `agent:frontend`, `agent:backend`, `agent:devops` (or
  `agent:optimizer` / `agent:security`, only when you want them). The agent opens a
  PR; it never merges. For a small, tightly coupled feature use `agent:team` with a
  `Roles: backend, frontend` line: several roles on one branch, one PR.
- **Alignment:** when an agent changes something other roles rely on (the API
  contract, data model, shared components, routes, env vars), it writes an entry in
  `docs/alignment/` and labels the PR `alignment-needed`.
- **CI** runs on every PR: build, lint, type check, contract drift check, tests,
  SBOM and license policy, vulnerabilities, secrets and misconfigurations.

## One-time setup

```bash
./scripts/install-skills.sh   # agent skills
./scripts/create-labels.sh    # agent:<role> and alignment-needed labels (needs gh)
```

On GitHub: install the Claude app (`/install-github-app` in Claude Code), add the
`CLAUDE_CODE_OAUTH_TOKEN` secret, and protect `main` (required CI, "Require branches
to be up to date before merging").

No secrets in the repository: keys go into GitHub secrets or local `.env` files,
which Git ignores.
