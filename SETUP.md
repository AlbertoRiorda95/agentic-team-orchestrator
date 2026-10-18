# SETUP.md — instructions for the Claude session that configures this template

You are setting up the **agent-team template** for a new project. The template
defines a team of agents: designer, frontend, backend and devops for everyday
work, optimizer and security that run only on explicit request,
plus the rules, hooks, workflows and gateway they need. It ships with
placeholder values written for a React + Node + Postgres app on GitHub; your
job is to replace them with the user's real project data.

If the user asked you to "read SETUP.md" or "set up this project", follow this
file from top to bottom, whether you run in Claude Code or in OpenCode. Talk to
the user in the language they use; keep every file you write in English.

The setup has two parts, both required:
1. **Configuration**: the interview, the edits, the checks (sections below up
   to "After editing: checks").
2. **Project design**: a design studio session that produces
   `docs/design/project.md` with `ready: yes`, unless it already exists. The
   setup is not finished without it: the team only implements what a ready
   spec describes.

## Ground rules

1. **Ask, don't guess.** Every value below comes from the user or from files
   that already exist in the repository. If an answer is missing or vague, ask
   again or propose a default and wait for confirmation.
2. **Read before asking.** If the repository already contains code (for example
   `package.json`, `pyproject.toml`, `go.mod`, `pom.xml`, `Cargo.toml`,
   `CMakeLists.txt`, `conanfile.*`, `Dockerfile`, `.github/workflows/`,
   `.gitlab-ci.yml`), inspect it first and turn your findings into proposals the
   user only has to confirm.
3. **One topic per round.** Ask the questions of one block at a time (blocks
   A–H below), at most five questions per round, then summarize what you
   understood before moving on.
4. **No edits until the summary is approved.** Collect all answers, show the
   complete plan of changes (file by file), get an explicit "yes", then edit.
5. **Never write secrets.** API keys and tokens go into the platform's secrets
   or into `infra/litellm/.env`, never into a tracked file. Only write the
   *names* of the secrets.
6. **Keep the files consistent.** The same folder names, commands and roles
   appear in several files; the "Where each answer goes" table lists them all.

## The interview

### A. Project
- Project name and a one-line description.
- Is this a new repository or an existing codebase?
- Git platform: GitHub, GitLab or other? Repository owner/name.
- Your username on that platform (for `CODEOWNERS`).

### B. Stack
- Languages and versions (for example TypeScript 5 / Node 22, Python 3.12,
  C++20, Go 1.23).
- Frontend framework, if any (React, Vue, Svelte, Angular, Qt, none…).
- Backend framework (Express, NestJS, FastAPI, Django, Spring, none…).
- Database and migration tool (Postgres + Prisma, MySQL + Flyway, SQLite…).
- Package manager and build system (npm, pnpm, poetry, uv, CMake + Conan…).
- Containers and deployment target (Docker/Podman, Kubernetes + Helm,
  Terraform, a PaaS, nothing yet).

### C. Commands
Ask for the exact command lines:
- install dependencies
- build
- run tests (all), and run a single test file if different
- lint / format, and lint a single file (used by `lint-frontend.sh`)
- start the dev server, with its port
- any type check or static analysis step

### C2. CI
The project CI (`.github/workflows/ci.yml`, `.gitlab/ci/ci.yml`) is written
for npm. Fill it in from the answers to B and C, or from what you find in the
repository (an existing CI is a source too: keep its steps):
- toolchain: the setup action on GitHub (`actions/setup-node`,
  `setup-python`, `setup-java`, `setup-go`...) and the image on GitLab;
- install, lint, build and test commands; the lockfile used as cache key;
- the install command of the `sbom-licenses` job: dependencies must be
  installed there (without running their scripts when the tool allows it),
  because license data come from them;
- a Dockerfile: on GitHub the image is built and scanned automatically; on
  GitLab ask whether to build and push it to the project registry and scan it.
Ask about the policies in `ci/scanners.env`: vulnerability threshold (default
`high`), license categories that fail the build (default `CRITICAL`, i.e.
forbidden licenses such as AGPL; add `HIGH` to block restricted ones such as
GPL), and whether some licenses must be moved between categories (a
`trivy.yaml` with a `license:` section).

### D. Folder layout
For each role, the folders it owns. Propose the defaults below, adjusted to
what you found in the repository, and ask the user to confirm or correct:

| Role | Default folders |
|---|---|
| frontend | `src/ui/`, `src/components/`, `src/styles/`, `src/api/` (client layer) |
| backend | `src/server/`, `migrations/`, `tests/integration/` |
| designer | `docs/design/` (specs only, no code) |
| devops | `.github/workflows/` or `.gitlab-ci.yml`, `Dockerfile*`, `compose*.yml`, `deploy/`, `charts/`, `infra/`, `Makefile` |
| optimizer | no folder of its own: works on tested code anywhere, on request |
| security | writes only `docs/security/`; reads everything, on request |

Also ask:
- Where the design tokens live (default `src/styles/tokens.css`), or whether
  there is no design system yet.
- Which paths are critical and need the user's review (default:
  `migrations/`, `src/server/auth/`, `.github/`, `.claude/`, `.opencode/`,
  `infra/`, `deploy/`).
- Whether to keep the security role and, if so: the staging host it may
  test besides `localhost` (never production), and which security tools are
  installed or should be (semgrep, OWASP ZAP, nuclei, the stack's dependency
  audit such as `npm audit` or `pip-audit`).
- Whether any role is not needed (for example no frontend in a CLI tool, no
  designer in a backend service). A removed role must disappear from every
  file in the table below.

### D2. API contract
- Where does the contract between frontend and backend live? OpenAPI file
  (default `docs/api/openapi.yaml`), shared TypeScript types or schemas, a
  GraphQL schema, protobuf files, or nothing yet (then propose creating
  `docs/api/openapi.yaml` from the existing routes).
- How does the frontend generate its types from it (for example
  `openapi-typescript`, `orval`, a codegen script)? If there is no generator
  yet, propose one and add the command to `## Commands`.
- Which changes count as breaking for this project (the default list is in
  `AGENTS.md` → API contract).

### E. Design system
- Brand colors, fonts, spacing scale, base components, breakpoints.
- If the user has none yet, keep the template's generic tokens and say so.

### F. Architecture
Which architecture of the guide will the team use?
- **A** — Claude Code on the user's computer with subagents
- **B** — agent teams (experimental)
- **C** — GitHub or GitLab, Claude only (issues as dashboard)
- **D** — GitHub Actions, multi-model (Claude + OpenCode)
- **E** — Multica self-hosted

For C and D also ask: API key or Claude subscription token
(`ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN`)? And whether they want
team tasks in CI (one issue, several roles in sequence on one branch, one
MR: `AGENTS.md` > Team tasks).

For D and E also ask:
- which roles run on non-Claude models (default: frontend and optimizer)
- which providers and models (default: DeepSeek for frontend, Mistral for
  optimizer) — the exact model IDs as the provider documents them
- direct keys in the platform secrets, LiteLLM on a server (domain name?), or
  a hosted gateway

### G. Models and effort
Propose the defaults and ask only whether to change them:

| Role | model | effort |
|---|---|---|
| designer | sonnet | medium |
| frontend | sonnet | medium |
| backend | opus | high |
| optimizer | opus | high |
| devops | opus | high |
| security | opus | high |

### H. Skills
`scripts/install-skills.sh` installs skills written for React, Postgres and
GitHub Actions. Show the list and ask which ones fit the stack:

| Skill | Fits when | Used by |
|---|---|---|
| frontend-design, web-design-guidelines | there is a web UI | designer |
| vercel-react-best-practices | React / Next.js | frontend, optimizer |
| webapp-testing | there is a web UI | frontend |
| tdd, diagnosing-bugs | always | frontend, backend |
| supabase-postgres-best-practices | Postgres | backend, optimizer |
| api-design-principles | there is an HTTP API | backend |
| security-review | always | security (preloaded), backend (on demand) |
| code-simplifier | always | optimizer |
| gha-security-review, github-actions-templates | GitHub Actions | devops |

For a stack the list doesn't cover, offer to search with `npx skills find
"<topic>"` and propose at most one or two skills per role: every installed
skill adds its description to every session.

## Where each answer goes

| Answer | Files to update |
|---|---|
| Project name, description | `AGENTS.md` (title), `README.md` (title and first paragraph: rewrite it for the project) |
| Stack | `AGENTS.md` → `## Stack` |
| Commands | `AGENTS.md` → `## Commands`; `docs/roles/frontend.md` (lint/test line); `.claude/hooks/gate-test.sh` (test command); `.claude/hooks/lint-frontend.sh` (file extensions and single-file linter); `.gitlab-ci.yml.example` (image, install steps) |
| Folder layout | `AGENTS.md` → `## How work is delegated`; `docs/roles/*.md` → `## Boundaries` of each role; `.github/CODEOWNERS`; `.claude/settings.json` → `Read(...)` deny rules for secret paths |
| Token location | `docs/roles/designer.md`, `docs/roles/frontend.md`, `.claude/skills/design-system/SKILL.md` |
| Design system | `.claude/skills/design-system/SKILL.md` (rewrite; keep it under ~60 lines) |
| Removed role | delete `docs/roles/<role>.md`, `.claude/agents/<role>.md`, `.opencode/agents/<role>.md`; remove it from `AGENTS.md` (sequence or on-demand roles), `CLAUDE.md`, `scripts/create-labels.sh`, the model expression in `.github/workflows/agents.yml`. For security also delete `.claude/hooks/security-*.sh`, `.claude/security-scope`, `docs/security/` and the matching `.gitignore` lines |
| Username | `.github/CODEOWNERS` |
| CI | `.github/workflows/ci.yml` and `.gitlab/ci/ci.yml` (toolchain, commands, cache key, build output); `ci/scanners.env` (policies); `trivy.yaml` only if license categories change |
| API contract | `AGENTS.md` → `## API contract` (path and generator); `docs/api/README.md`; `docs/roles/frontend.md` and `docs/roles/backend.md` if the wording differs; `.github/CODEOWNERS` (add the contract path) |
| Commands allowed in CI | `--allowedTools` in `.github/workflows/agents.yml` and `claude.yml` (replace `Bash(npm:*)`, `Bash(npx:*)` with the stack's tools), `.gitlab-ci.yml.example` |
| Security scope and tools | `.claude/security-scope` (one host per line, never production); the dependency-audit command in `docs/roles/security.md` → `## What you check` item 6 |
| Architecture | see "Cleanup by architecture" below |
| Team tasks in CI | keep the `team` job in `.github/workflows/agents.yml` and `agent:team` in `scripts/create-labels.sh`, or the `claude-team` job in `.gitlab-ci.yml.example`; if not wanted, remove them and the `## Team tasks` section of `AGENTS.md` |
| Subscription token | `.github/workflows/*.yml`: replace `anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}` with `claude_code_oauth_token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}` |
| Non-Claude roles, providers | `.github/workflows/agents.yml` (secrets in `env`, `model:` expression), `opencode.json`, `.opencode/agents/` (one file per non-Claude role, permissions as in the existing ones), `infra/litellm/litellm-config.yaml`, `infra/litellm/docker-compose.yml`, `infra/litellm/.env.example` |
| LiteLLM domain | `infra/litellm/Caddyfile`, `infra/litellm/create-key.sh`, `opencode.json` (`baseURL`) |
| Models and effort | `model:` and `effort:` in `.claude/agents/*.md`; the `--model` expression in `.github/workflows/agents.yml` |
| Skills | `scripts/install-skills.sh`; the `skills:` list and the closing note of each `.claude/agents/*.md`; the skill names in `CLAUDE.md` |
| No web UI | remove the `playwright` MCP server from `.claude/agents/designer.md` (or the designer role) and the frontend lint hook if there is no frontend |

Placeholders that are *not* marked `CUSTOMIZE` but still depend on the stack:
`src/...` paths and `npm` commands inside `docs/roles/*.md` and `AGENTS.md`,
`tokens.css`, the deny list in `.claude/settings.json`, the `npm test*` /
`npm run lint*` permissions in `.opencode/agents/*.md`.

## Cleanup by architecture

| Architecture | Keep | Delete |
|---|---|---|
| A | `AGENTS.md`, `CLAUDE.md`, `docs/`, `.claude/`, `.mcp.json`, the project CI (`ci/` and `ci.yml`, or the GitLab files without `agents.yml`) | the agent workflows (`agents.yml`, `claude.yml`, `claude-review.yml`), `.gitlab/ci/agents.yml` and its include, `.opencode/`, `opencode.json`, `infra/`, `scripts/create-labels.sh` |
| B | as A; set `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` to `"1"` in `.claude/settings.json` | as A |
| C on GitHub | as A, plus `.github/` and `scripts/create-labels.sh`; remove the `opencode` job from `agents.yml` | `.opencode/`, `opencode.json`, `infra/`, `.gitlab-ci.yml.example`, `.gitlab/` |
| C on GitLab | as A, plus `.gitlab/ci/agents.yml`; rename `.gitlab-ci.yml.example` to `.gitlab-ci.yml` | `.github/workflows/`, `.opencode/`, `opencode.json`, `infra/`, `scripts/create-labels.sh` (move `.github/CODEOWNERS` to `.gitlab/CODEOWNERS`, where GitLab reads it) |
| D | everything; `infra/litellm/` only with LiteLLM on a server | `.gitlab-ci.yml.example`, `.gitlab/`; `infra/` with direct keys or a hosted gateway |
| E | `AGENTS.md`, `docs/`, `.opencode/`, `opencode.json`, `infra/litellm/`, the project CI | the agent workflows, `.gitlab/ci/agents.yml` and its include |

## After editing: checks

Run these and fix anything that fails before reporting:

```bash
grep -rn --exclude=SETUP.md "CUSTOMIZE\|<name>\|<model>\|<version>\|your-username\|your-domain" .   # only what you left on purpose
claude plugin validate .claude/agents      # agent frontmatter loads
bash -n .claude/hooks/*.sh scripts/*.sh infra/litellm/*.sh ci/*.sh 2>/dev/null
chmod +x .claude/hooks/*.sh scripts/*.sh infra/litellm/*.sh 2>/dev/null
python3 -c "import json; [json.load(open(f)) for f in ['.claude/settings.json','.mcp.json']]"
echo '{"tool_input":{"command":"terraform apply"}}' | ./.claude/hooks/block-infra-commands.sh; echo "exit $? (must be 2)"
./.claude/hooks/alignment-check.sh; echo "exit $? (must be 0: no open entries yet)"
grep -q '^ready: yes' docs/design/project.md && echo "project design ready" || echo "project design NOT ready"
# with the security role:
echo '{"tool_input":{"command":"curl https://example.com"}}' | ./.claude/hooks/security-scope.sh; echo "exit $? (must be 2)"
echo '{"tool_input":{"command":"curl http://localhost:3000/api"}}' | ./.claude/hooks/security-scope.sh; echo "exit $? (must be 0)"
```

If the network allows it, run the CI security steps once locally: they
install their own tools in `~/.local/bin` and write to `reports/`:

```bash
./ci/install-scanners.sh && ./ci/scan.sh sbom-licenses && ./ci/scan.sh vulnerabilities
```

Validate the YAML files you changed (workflows, LiteLLM config) with any YAML
parser available. Keep `<version>` placeholders only where the user chose to
pin versions later, and list them in the report.

## Project design (required)

The agents implement only what a ready spec describes (`AGENTS.md` > Specs
before code), so the project needs its design before the first task. Tell the
user this step is part of the setup, not an optional extra.

1. **If `docs/design/project.md` exists with `ready: yes`:** read it, check it
   against the interview answers (stack, roles, contract) and report any
   difference. This part is done.
2. **Otherwise, run a design studio session for the project.** Follow
   `docs/roles/design-studio.md`, with `docs/design/_project-template.md` as
   the template and `docs/design/project.md` as the running draft. In an
   existing codebase, first draft it from the code (routes, models, pages,
   README) and ask the user to confirm and complete it instead of starting
   from zero. Rounds:
   1. product, users and their roles, out of scope;
   2. core flows, with their error cases;
   3. screens and main components;
   4. domain model;
   5. API surface: write the first version of the contract in the format
      chosen in D2 (default `docs/api/openapi.yaml`);
   6. integrations and non-functional requirements (performance, security
      and privacy, accessibility, devices, languages);
   7. design direction: update `.claude/skills/design-system/SKILL.md` with
      what was decided;
   8. roadmap: milestones and their features, one future spec each.
3. Set `ready: yes` only when "Open questions" is empty and the user confirms.
4. Commit the project design, the contract and the design-system skill in a
   commit of their own, separate from the configuration.

The user can skip this only by saying so explicitly ("skip the project
design"). Then create `docs/design/project.md` from the template with
`ready: no` and the line `skipped: <date>, by the user`, and tell them
clearly that no implementation task can start until it is ready: they can
resume any time with `/design-studio project`.

## Report to the user

End with:
1. the answers you used, in a short table;
2. the files changed, created and deleted;
3. what is still open (versions to pin, secrets to create, labels to run,
   branch protection to enable, the CI as a required check on `main`), as a checklist;
4. a reminder that optimizer and security run only on request, and that a
   security assessment is best run once the application is complete;
   on GitHub, a reminder to enable branch protection on `main` with "Require
   branches to be up to date before merging" and to run
   `./scripts/create-labels.sh` (it also creates `alignment-needed`); on
   GitLab, to create the `alignment-needed` label and to pass `TASK_ID`
   when triggering the agent job;
5. the state of the project design (ready, or skipped) and the roadmap
   features, with the first one to design: `/design-studio <feature>`;
6. the next command to run, for example `./scripts/install-skills.sh`, then
   `claude` and "list the available agents".

Finally ask whether to delete this `SETUP.md`. It is not needed once the
project is configured, and every agent session that reads the repository
would otherwise see it.
