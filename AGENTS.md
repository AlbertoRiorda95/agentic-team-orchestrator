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
- `apps/web/`, `apps/mobile/`, `packages/`, root `package.json`,
  `package-lock.json` and `tsconfig*.json` → frontend
- `backend/` (except `backend/Dockerfile`), `docs/api/openapi.yaml` → backend
- `docs/design/`, UI review → designer
- `.github/workflows/`, `ci/`, `Dockerfile*` (including `backend/Dockerfile`),
  `.dockerignore`, `compose*.yml`, `Makefile`, `deploy/`, `charts/`, `infra/` → devops
- Optimizing code that already works and is tested → optimizer

Two agents never edit the same file in the same round. If a task crosses
a boundary, split it into two tasks with an explicit dependency.

## Standard feature sequence
1. designer writes the spec in `docs/design/`
2. backend updates the API contract, if the feature changes it
3. backend and frontend implement in parallel, against that contract
4. designer reviews the implementation
5. frontend applies the feedback
6. devops updates pipeline, image and manifests if the feature needs it
7. the MR is opened

Not every feature involves every role. A style change does not need
devops; an infrastructure migration does not need the designer. Involve
only the roles the task actually touches.

## On-demand roles
These two roles are never part of the standard sequence. Delegate to them
only when the user asks explicitly.
- optimizer: when the user asks for an optimization or a measurement shows
  a performance problem. Only with green tests.
- security: when the user asks for a security assessment, typically once the
  application is complete or before a release. It reports findings; the
  owning roles fix them as separate tasks.

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

## Alignment changes
A change is an alignment change when another role relies on what you
changed: the API contract, the data model, a shared component or design
token, a route or user flow, an environment variable or port, the deployment
interface.

When you make one:
1. Copy `docs/alignment/_template.md` to
   `docs/alignment/<yyyy-mm-dd>-<task-id>.md` and fill it in, with
   `status: open`. One file per change, so parallel branches never conflict.
2. In the MR description add an `## Alignment impact` section that links the
   entry (write "none" when there is none). In CI also add the
   `alignment-needed` label to the MR.
3. Do not adapt other roles' code yourself.

What happens next depends on where you run:
- **Local session (Claude Code with subagents or agent teams):** the lead
  handles it right away. First designer reviews the change against the specs,
  updates `docs/design/` if needed and writes the follow-up actions per role
  in the entry. Then the lead delegates each action to its role. Finally the
  entry gets `status: resolved` and a short resolution. The lead stops and asks
  the user only when designer sets `decision-needed: yes` (for example a
  breaking API change or a visible UX change).
- **CI (GitHub Actions):** agents never start other
  agents, except the coordinator of a team task (below). The entry and the
  label are the signal: the user reviews them and creates the alignment
  tasks, designer first, then the affected roles.

## Team tasks
A team task is one issue carried out by several roles in sequence on the same
branch, ending in one MR. The user asks for it explicitly: the `agent:team`
label on GitHub (with a `Roles: backend, frontend` line in the issue body),
or a request in a local session.
- A coordinator delegates only to the listed roles, in the listed order, and
  writes no code itself.
- Each role works within its own boundaries and commits and pushes before the
  next one starts.
- Alignment entries that concern listed roles are handled inside the task;
  the others stay open and are reported in the MR.
- Use team tasks for small, tightly coupled features. Larger work stays split
  into separate tasks, so that each MR remains reviewable.

## Splitting issues
In CI the user can ask for a proposal that splits one issue into task issues,
one per role: the `agent:split` label on GitHub, `SPLIT_ISSUE` on GitLab. The
proposal is a plan in the format at the top of `scripts/split-issue.py`; the
user approves it (`@claude ok`) and the script creates exactly that. Rules for
the plan:
- One task per role and per boundary (see "How work is delegated"): a task
  never makes two roles edit the same files.
- Follow the standard feature sequence: the API contract first when the
  feature changes it, then backend and frontend against it; devops only if
  the pipeline, the image or the manifests change.
- No ready spec for the work: propose a single designer task that writes it,
  or say in a comment that a design studio session with the user is needed.
  Never plan implementation tasks on missing design.
- optimizer and security only when the issue asks for them explicitly.
- At most 6 tasks. If more are needed, say so and propose splitting the issue
  into features first.
- Every task has acceptance criteria someone can check without reading the
  code, and lists the files or folders it touches.
- Suggest a team task (`team` in the plan) when the work is small and tightly
  coupled (see "Team tasks").
- Never add labels: the user starts each task.

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
- One branch per task, named `feat/<task-id>-<slug>` (in GitHub Actions, the
  branch the action creates for you).
- Before opening the MR, bring your branch up to date with `main` and run the
  tests again. Where you are not allowed to rebase (the Claude GitHub action),
  say in the MR that the branch must be updated before merging.
- Before opening the MR, check whether `main` changed the API contract or
  `docs/alignment/` since you started; if it did, adapt or report it.

## CI
Every MR runs the project CI: build, type check, test, static analysis, SBOM
and license report, license policy, vulnerabilities, secrets and
misconfigurations (`ci/scan.sh`).
- A red CI is part of your task: fix the cause, never weaken the check. Do not
  edit `ci/scanners.env`, skip a test or add an ignore rule without the user's
  explicit approval in the MR.
- Static analysis: semgrep fails the MR on the findings your change
  introduces (details in `semgrep.txt`, artifact `static-analysis`). Fix the
  code. If you think a finding is a false positive, do not suppress it
  yourself: explain it in the MR under `## Static analysis` and let the user
  decide. A `nosemgrep: <rule-id>` comment, with the reason next to it, only
  with the user's approval.
- UI tests: when `playwright.config.ts` exists, the `ui` job runs the tests
  in `e2e/` and keeps the report and the screenshots per viewport (artifact
  `ui-report`). A screen or state without its UI test is not done.
- When you run outside CI (a local session), wait for the checks after
  opening the MR (`gh pr checks --watch`), fix what fails and push again.
  Agents that run inside CI jobs do not wait: the user sends the failures
  back.
- Workflow files: after editing anything in `.github/workflows/`, run
  `actionlint` (the `Workflow lint` check runs it on every PR). A job-level `if`
  can use only the `github`, `needs`, `vars`, `inputs` and `matrix` contexts:
  `hashFiles()` works in steps only, and one in a job `if` makes GitHub reject
  the whole file, so no job runs.

## Rules for everyone
- Small commits, messages in English, imperative mood.
- Nobody pushes to `main`. Nobody merges. Nobody closes an issue.
- If a requirement is ambiguous, stop and ask; do not guess.
