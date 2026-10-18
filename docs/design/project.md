---
ready: yes
updated: 2026-10-18
---

# DevOrchestrator — project design

## Product
Application for managing a software development team made of AI agents.
Tagline: "AI agents. Real software." Web app, mobile app and API.

DevOrchestrator is **architecture F** of `docs/general/guide.md` (§2.7, §11.2–11.4):
a self-hosted service that **runs the agents itself** with the Claude Agent SDK
(Python `claude-agent-sdk`), instead of delegating to GitHub Actions. Its parts
follow §11.4: intake (webhooks, dashboard API), store (Postgres), scheduler (locks,
budgets, concurrency), task pipeline (steps, tests, commit, push), alignment
control, workspace (one Git worktree per task), runners, Git platform adapter,
Studio mode (design conversations that produce specs and tasks), and the
dashboard (the web app; the mobile app on top).

Why it exists: queues with priorities, automatic retries, budgets per task,
execution on your own infrastructure, and automatic alignment handling with
rules you decide; the things architecture C cannot give (guide §2.7, §11.4).

Purpose: a **demo project** that validates the agent-team workflow of this
template (architectures A and C are used to build it); architecture F is a
realistic use case to prove that workflow end to end. Internal tool for one
team: not a product for sale, not multi-tenant.

One installation manages **several projects**: each project is one Git
repository configured with this template (AGENTS.md, `.claude/`, `docs/roles/`),
with its own budget and settings.

Web and mobile are **full twins**: everything you can do on the web you can do
on the phone, so the agents' work can be followed and steered without a PC
(for example while travelling).

## Users and roles
One team, one installation.

| User type | Goals | Permissions |
|---|---|---|
| owner | run the installation | everything a lead can do, plus users, projects (repositories), credentials, role configuration, budgets |
| lead | get features built | create and edit tasks and studio sessions, answer `waiting_human` decisions, stop, retry and cancel tasks |
| viewer | follow the work | read-only: tasks, logs, specs, costs |

Code review of the PRs stays on GitHub.

Agent roles are fixed for now: designer, frontend, backend, devops, optimizer,
security, with their prompts read from the target repository's `docs/roles/`
(the orchestrator contains no prompts of its own, guide §11.4).

## Core flows
GitHub holds the repositories and runs their CI (tests, vulnerabilities,
licenses); it is not an intake channel. Tasks are created only in the app.

1. **Add a project** (owner). Pick a GitHub repository; the orchestrator clones
   it, checks the template configuration (`AGENTS.md`, `.claude/`, `docs/roles/`),
   and the owner sets budget, defaults and alignment policy.
   Errors: no access to the repository; template configuration missing (list
   what is missing, project not activated); clone fails.
2. **Studio session** (lead). One design conversation per feature with the
   designer agent; the draft is committed to `design/<feature>` after every
   round. "Finalize" checks the spec's checklist and open questions, then opens
   the design PR. When it is merged, the breakdown becomes tasks (`blocked` when
   they depend on others, otherwise `queued`).
   Errors: checklist incomplete (show what is missing); session interrupted
   (resume where it stopped).
3. **Create a task** (lead), in the app only. Title, description, the spec
   (`ready: yes`), roles in order (the steps), priority, budget, alignment
   policy, and **the model of each step**: defaults to the role's configured
   harness and model, can be changed per task.
   Errors: no ready spec for an implementation task; model not available for
   the chosen harness.
4. **Task run** (automatic). The scheduler claims the task (one task per branch,
   concurrency limits per role and overall, remaining budget) and prepares a
   worktree on `feat/<id>`. For each step: sync with `main`, run the agent
   (Claude Agent SDK or OpenCode) streaming its progress, run the tests, commit
   and push, check `docs/alignment/`. Then the PR is opened on GitHub and the
   CI checks are followed; a red test run or red CI inserts a fix step for the
   same role with the failure log, **at most 2 attempts**, then the task waits.
   The task ends in `in_review`, and `done` when the PR is merged. The
   orchestrator never merges.
   Errors: rebase conflict, tests or CI still red after 2 attempts, budget
   exhausted, agent error or timeout, open alignment entry with policy `ask`
   → `waiting_human` (or `failed` for agent errors), always with a written
   reason.
5. **Human decision** (lead). Push notification and in-app inbox. The lead
   either picks a structured action (approve, reject, retry, raise budget,
   cancel) or **writes a free-text reply that resumes the same agent session**
   (SDK `resume`).
   Errors: decision is stale because the task changed state meanwhile (show
   the current state, ask again).
6. **Control a task** (lead): stop a running task, retry a failed one, cancel,
   change priority.
   Errors: stop during commit or push (finish the Git operation, then stop, so
   the branch stays consistent).
7. **Monitoring** (everyone): projects and tasks with their state, live log of
   each step, costs per task, role, model and project.
   Errors: stream disconnected (reconnect and replay the missed events).
8. **Settings** (owner): users and roles; role configuration (harness, model,
   `maxTurns`, concurrency); budgets; credentials.
   Errors: invalid credentials (tested when saved).

9. **Change request from the diff** (lead), only while the task is
   `in_review`. In the step diff the lead comments on lines (file, line, text)
   and sends them together: a new **review step** for the same role is added,
   with the comments as instructions; it runs like any step (tests, commit,
   push, CI) and the task returns to `in_review` when it is done.
   Errors: the commented line no longer exists in the latest commit (the
   comment is sent with its original commit and context).
10. **Configure providers** (owner). Add a provider (Anthropic API key, Claude
   subscription token, cloud API key for OpenCode, or self-hosted server with
   base URL), test the connection, read its available models; roles and task
   steps then choose among those models.
   Errors: connection test fails; a model used by a role disappears from the
   provider (the role is flagged, its tasks wait).

11. **Security assessment** (owner, lead), on demand only. Choose model and
   ref (latest `main` by default); the app shows an estimated cost range
   (average turns of past assessments on the project × the model's cost per
   turn, or 60–120 turns without history) and checks it against the budgets.
   The security agent runs in a worktree of that ref: static analysis
   (semgrep, `npm audit`, `pip-audit`) and dynamic tests against the app it
   starts there with `docker compose`, only on `localhost` of an isolated
   network. Results: findings by severity, report, actual cost. From a finding:
   create a fix task for the owning role, accept the risk with a reason, or
   re-test selected findings.
   Errors: the app does not start (static results only, reported as such);
   budget exceeded mid-run (stop, partial report).

Optimizer runs as an ordinary task with the optimizer role; no dedicated screen.

Alignment policy: `ask` by default (the task waits for the lead), `auto`
(designer, then the affected roles, at most 2 rounds) can be chosen per project
or per task.

## Screens
Navigation: web, left sidebar (Overview, Inbox with badge, Tasks, Studio,
Projects, Agents, Costs, Settings) and a project filter on top ("All projects"
by default). Mobile, bottom tabs (Overview, Tasks, Inbox, Studio, More: Projects,
Agents, Costs, Settings) with the same filter. Every screen exists on both.

| Screen | Purpose | Main components |
|---|---|---|
| Login | sign in | form (method in round 6) |
| Overview | everything at a glance | counters (running, waiting for you, in review, failed); spend today and this month vs budget; "waiting for you" list; recent PRs |
| Tasks | the work queue | kanban by state on web, list grouped by state on mobile; filters by project, role, priority |
| Task detail | follow one task | header (state, priority, branch, PR link, budget bar); step timeline (role, model, state, cost, duration); live log of the selected step (agent text, tool calls; tool results collapsed); CI checks; alignment entries; read-only diff per step; while the task is `in_review`, line comments (file, line, text) that are sent as one change request; actions: stop, retry, cancel, priority |
| New task | create a task | title, description, spec picker (`ready: yes` only), step builder (role + model, reorderable), priority, budget, alignment policy |
| Inbox | human decisions | `waiting_human` items with reason; detail with context (step log, alignment entry, CI failure), structured actions, reply box that resumes the agent |
| Studio | design and spec review | list of specs of the project (`docs/design/`, with their `ready` state) and of sessions; spec viewer (rendered); chat with the designer with the live draft (side panel on web, tab on mobile); "Finalize" with the checklist result; design PR link |
| Projects | repositories | list with state and budget; add-project wizard (repository, configuration check, budget, defaults); project settings |
| Security | on-demand assessments per project (owner, lead) | start form: model, commit or branch, estimated cost range checked against budgets; live log; results: counts by severity, findings (title, where, impact, fix, owning role; proof expandable), rendered report, actual cost vs estimate, duration, turns; history; per finding: create fix task, accept risk (with reason), re-test selected findings |
| Agents | providers the roles run on | provider list (type, state, models count); add or edit a provider: type, credential or base URL, "test connection"; available models read from the provider (`/models`) with refresh, optional price per token |
| Costs | spend | by project, role, model and time; most expensive tasks |
| Settings | administration (owner) | users and roles; role configuration (harness, model, `maxTurns`, concurrency) |

## Domain model
PostgreSQL. Git stays the source of truth for specs, code and alignment entries;
the database indexes them and holds everything the orchestrator owns.

| Entity | Key fields | Relations |
|---|---|---|
| User | email, name, role (`owner`/`lead`/`viewer`), active | has PushDevices; creates Tasks, Decisions, ReviewComments |
| Project | name, GitHub repository, default branch, clone path, config check (ok, missing items), budget per period, created at (anchors the budget periods), default alignment policy, active | has Tasks, Specs, StudioSessions, RoleConfigs, SecurityAssessments |
| Provider | type (`anthropic_api`/`claude_subscription`/`cloud_api`/`self_hosted`), name, base URL, encrypted credential, harness (`claude`/`opencode`), connection state, last check | has Models |
| Model | provider, model ID as the provider names it, display name, input and output price per Mtok (optional), available | used by RoleConfigs, Steps, SecurityAssessments |
| RoleConfig | role, model, `max_turns`, `max_concurrent`; global, or per project overriding the global one | → Model, → Project (optional) |
| Spec | path in `docs/design/`, feature, `ready`, updated, commit SHA (index of the repository files) | → Project; used by Tasks, StudioSessions |
| StudioSession | feature, branch `design/<feature>`, SDK session ID, state (`active`/`in_review`/`merged`/`abandoned`), design PR URL | → Project, → Spec; has StudioMessages |
| StudioMessage | author (user or designer), text, time | → StudioSession |
| Task | title, description, branch `feat/<id>`, priority P0–P3, budget, spent, alignment policy, state (`blocked`/`queued`/`running`/`waiting_human`/`in_review`/`done`/`failed`/`cancelled`), waiting reason, PR URL, origin (`manual`/`studio`) | → Project, → Spec, depends on Tasks; has Steps |
| Step | position, role, model, instructions, reason (`planned`/`alignment`/`fix`/`review`/`reply`), state (`pending`/`running`/`done`/`failed`/`skipped`), attempt, cost, tokens, duration, summary, SDK session ID, commit SHA | → Task, → Model; has Events |
| Event | sequence (monotonic, for replay), kind (`text`/`tool_use`/`tool_result`/`test`/`ci`/`state`), JSONB payload, time | → Task or SecurityAssessment, → Step |
| Decision | reason (`alignment`/`budget`/`tests`/`ci`/`conflict`/`agent_question`), details, state (`open`/`answered`/`stale`), action, reply text, answered by | → Task, → Step |
| ReviewComment | file, line, commit SHA, text, author, state (`draft`/`sent`/`addressed`) | → Task, → Step that wrote the code, → review Step |
| CiCheck | name, state, conclusion, URL, log excerpt | → Task |
| AlignmentEntry | file in `docs/alignment/`, affected roles, `decision_needed`, state | → Task, → Step that opened it |
| SecurityAssessment | model, commit assessed, estimated cost (low–high), actual cost, state (`queued`/`running`/`done`/`failed`/`cancelled`), report (Markdown, stored in the database: `docs/security/` is not committed), started, finished | → Project, → Model; has Findings, Events |
| Finding | severity (`critical`/`high`/`medium`/`low`/`suspected`), title, where, impact, proof, fix, owning role, state (`open`/`task_created`/`fixed`/`accepted`) | → SecurityAssessment, → Task created from it |
| PushDevice | Expo push token, platform | → User |
| AuditEntry | user, action, target, details, time | → User |

- Branch locks: a unique constraint on the active task's branch, claimed with
  `SELECT … FOR UPDATE SKIP LOCKED`; they survive a restart.
- Costs are summed from Steps and SecurityAssessments; totals are queries, not counters.
- Budgets: per task; per project per **30-day period anchored at the project's
  creation date**; and an installation ceiling per 30-day period anchored at the
  installation date. When a period's budget is reached, nothing new starts in
  that scope; running steps finish.
- Retention: Events kept in full for 90 days, then only summaries and costs.
- Credentials encrypted at rest, key outside the database (round 6).

## API surface
The first version of the contract is in `docs/api/openapi.yaml` (v0.1.0,
OpenAPI 3.1, 76 operations). From the first backend task on it is exported from
FastAPI with `make openapi`.

Conventions: base path `/api/v1`; JSON; UTC ISO 8601 timestamps; UUID ids;
errors as RFC 9457 `application/problem+json` (with `errors[]` for validation);
cursor pagination (`cursor`, `limit`, `next_cursor`); long operations return
`202` and report progress on the stream; credentials are write-only.

**Live updates: Server-Sent Events** on `GET /stream` (filters by project,
task, studio session, assessment). Each message carries `id` = Event.sequence,
so a client reconnects with `Last-Event-ID` and replays what it missed. Event
payloads are OpenAPI schemas (`Event*`, discriminated by `kind`), so web and
mobile get generated types; mobile uses `react-native-sse`.

| Area | Endpoints |
|---|---|
| Auth | `/auth/login`, `/auth/refresh`, `/auth/logout`, `/me` (method confirmed in round 6) |
| Users, installation | `/users`, `/users/{id}`; `/installation` (installation budget) |
| Projects | `/projects`, `/projects/{project_id}`, `…/check`, `…/budget` |
| Providers, models | `/providers`, `/providers/{id}`, `…/test`, `…/models/refresh`; `/models`, `/models/{id}` |
| Role configs | `/role-configs`, `/role-configs/{role}`, `/projects/{project_id}/role-configs/{role}` |
| Specs | `/projects/{project_id}/specs`, `…/specs/content?path=` |
| Studio | `/projects/{project_id}/studio-sessions`, `/studio-sessions/{id}`, `…/messages`, `…/finalize`, `…/abandon` |
| Tasks, steps | `/tasks`, `/tasks/{id}`, `…/stop`, `…/retry`, `…/cancel`, `…/steps`, `…/ci-checks`, `…/alignment-entries`; `/steps/{id}/events`, `/steps/{id}/diff` |
| Review | `/tasks/{id}/review-comments`, `…/send`; `/review-comments/{id}` |
| Decisions | `/decisions`, `/decisions/{id}`, `…/answer` (409 when stale) |
| Security | `/projects/{project_id}/security-assessments`, `…/estimate`; `/security-assessments/{id}`, `…/cancel`, `…/findings`, `…/retest`; `/findings/{id}`, `…/fix-task` |
| Costs, overview | `/costs?group_by=`, `/costs/top-tasks`, `/overview` |
| Devices, audit | `/push-devices`, `/push-devices/{id}`; `/audit` |
| Stream, health | `/stream` (SSE); `/health`, `/health/ready` |

## Integrations
| Service | Used for | When it fails |
|---|---|---|
| GitHub (a **GitHub App** installed on the project repositories: contents, pull requests, checks; short-lived installation tokens) | clone, push `feat/*` and `design/*` branches, open PRs, read CI checks and merge state | operations retry with backoff; the task waits with reason "GitHub unreachable" after 3 failures; nothing is lost, the worktree stays |
| GitHub status updates: **polling** every 30–60 s for open PRs and their checks (testing behind a VPN); **webhooks** replace polling in production | `in_review` → `done` on merge, CI results, design PR merged → tasks created | polling resumes from the last known state; webhook deliveries are idempotent (delivery id recorded) |
| Claude Agent SDK (Python `claude-agent-sdk`, `settingSources: ["project"]`, `permissionMode: "acceptEdits"`, never `bypassPermissions`) | runs Claude steps, studio sessions, security assessments; returns cost per run | step `failed` with the error; retry is manual |
| OpenCode CLI | runs steps on non-Claude providers (cloud APIs, self-hosted servers) | as above; cost read from the provider response or LiteLLM when available, otherwise estimated from tokens and the model's prices |
| Providers (Anthropic API, cloud APIs, self-hosted OpenAI-compatible servers) | the models | connection test on save; a model that disappears flags its role and its tasks wait |
| Expo push service | notifications for `waiting_human`, `failed`, `in_review`, assessment done | the in-app inbox is the source of truth; push is best effort |
| Docker (on the orchestrator host) | runner containers; the app under test for security assessments, on an isolated network | assessment continues with static analysis only, reported as such |

## Non-functional requirements
- **Deployment (testing):** one server with Docker Compose: API, scheduler/worker,
  Postgres, runner containers; reachable only through a VPN (Tailscale), so
  GitHub is polled. **Production** (later, provider to be chosen): public HTTPS
  domain, GitHub webhooks instead of polling. The code supports both modes by
  configuration.
- **Authentication:** email and password, accounts created by the owner;
  Argon2id hashes; short-lived JWT access token plus rotating refresh token;
  tokens in secure storage on mobile (`expo-secure-store`).
- **Authorization:** checked on the server for every endpoint and stream
  event by user role (owner, lead, viewer).
- **Secrets:** provider credentials and the GitHub App key encrypted at rest
  (key from the environment, never in the database or the repository); never
  returned by the API, never written to logs or events.
- **Agent isolation:** runners in containers with write access to their
  worktree only; the GitHub App cannot push to `main` (branch protection); the
  target repository's `.claude/settings.json` hooks and deny rules stay active.
- **Limits:** default concurrency 1 per role, 3 in total; `maxTurns` per role;
  timeout 60 minutes per step; budgets per task, project and installation.
- **Performance:** live log events reach the clients in under 2 s.
- **Reliability:** state in Postgres, the orchestrator resumes after a restart;
  branch locks in the database; daily Postgres backups.
- **Accessibility:** WCAG 2.2 AA on web and mobile.
- **Devices:** web on current Chrome, Firefox, Safari, Edge; mobile on
  **Android** first (a development build for push notifications, built
  locally, no EAS yet); iOS in a later release.
- **Language:** English only.

## Design direction
Dark theme only; brand palette, Inter + JetBrains Mono, shadcn/ui (web) and
React Native Reusables + NativeWind (mobile) on shared tokens. Details in the
design-system skill; brand assets in `docs/design/brand/`.
- Web: a dense developer tool in the style of Linear, GitHub and Vercel;
  keyboard shortcuts. Mobile: airy, cards, comfortable rows.
- Agent roles have avatars in the logo's style, one color per role, always
  with the role name; state is never shown by color alone.
- The brand gradient only on the logo, login and empty-state calls to action.
- Subtle motion under 200 ms, disabled with reduced motion.

## Out of scope for now
- Two-factor authentication.
- iOS app (later release); EAS builds.
- GitLab: GitHub only; the platform adapter stays isolated so GitLab can be added.
- Configurable agent roles.
- Multi-tenancy, billing, public sign-up.

## Roadmap
Every feature spec covers **web and mobile together**. Studio is the first
product feature: it comes right after the foundations it needs.

| Milestone | Features (one spec each) |
|---|---|
| M0 Foundations | `foundations` (Makefile, compose, FastAPI skeleton with `/health`, web and mobile skeletons, `packages/tokens`, API client generation, CI complete); `app-shell` (navigation, login screen, theme); `auth-and-users` |
| M1 Studio | `projects` (GitHub App, clone, config check, polling); `providers-and-models` (Anthropic API first); `role-config`; `live-stream` (SSE with replay); `studio` (chat with the designer, spec review, finalize, design PR; when merged, the breakdown becomes tasks that wait in the queue until M2) |
| M2 Single-task loop (guide stages 1–2) | `task-run` (one role, Agent SDK, worktree, commit and push, PR, CI polling); `task-detail` (live log, steps, CI); `task-board` |
| M3 Multi-step and the human in the loop (stages 3, 4, 7) | `multi-step-tasks` (step builder, model per step); `decisions-inbox` (actions and reply with resume); `alignment-control` (`ask`, then `auto`); `ci-fix-loop` (2 attempts); `budgets-and-costs` (budgets, Costs, Overview) |
| M4 Review and notifications | `diff-and-review` (diff, line comments, review step); `push-notifications` (Android) |
| M5 Other models and security (stage 6) | `opencode-runner` (cloud APIs, self-hosted servers); `security-assessments` |
| M6 Production | `webhooks` (replace polling); `deployment` (hosting provider); `audit-log`; `retention-and-backups` |

First spec to design: `foundations`.

## Decisions
- 2026-10-18 — Product name DevOrchestrator, repository agentic-team-orchestrator — chosen by the user.
- 2026-10-18 — Dark theme only — chosen by the user.
- 2026-10-18 — DevOrchestrator is the guide's architecture F: it runs agents itself via the Agent SDK — user's choice.
- 2026-10-18 — Single team, self-hosted, not for sale — user's choice; no multi-tenancy.
- 2026-10-18 — Demo project to validate the A/C workflow, with F as the use case — user's statement.
- 2026-10-18 — Several projects (repositories) per installation — user's choice.
- 2026-10-18 — Mobile is a full twin of the web app — to follow agents without a PC.
- 2026-10-18 — OpenCode runner (non-Claude models) included in scope — user's choice.
- 2026-10-18 — User roles owner, lead, viewer; PR review stays on GitHub — user's choice.
- 2026-10-18 — Tasks are created only in the app; GitHub holds the repositories and their CI — user's choice.
- 2026-10-18 — Model selectable per task step, defaulting to the role configuration — user's request.
- 2026-10-18 — Up to 2 automatic fix attempts on red tests or CI, then waiting_human — user's choice.
- 2026-10-18 — Alignment policy `ask` by default — until the workflow is trusted.
- 2026-10-18 — Human decisions: structured actions and free-text replies that resume the agent session — user's choice.
- 2026-10-18 — Specs are reviewed inside Studio, not in a separate screen — user's choice.
- 2026-10-18 — Kanban on web, grouped list on mobile — user's choice.
- 2026-10-18 — Live log shows text and tool calls, tool results collapsed — user's choice.
- 2026-10-18 — Per-step diff in the app, so a task can be steered without opening the PR — user's choice.
- 2026-10-18 — Diff line comments become a review step for the same role, only in `in_review` — user's choice (a).
- 2026-10-18 — "Agents" screen configures providers (API keys, subscription, self-hosted servers, their models); roles stay fixed — user's confirmation.
- 2026-10-18 — Budgets per task, per project and per installation, in rolling 30-day periods from the creation date — user's choice.
- 2026-10-18 — Priority P0–P3, FIFO within a priority — user's choice.
- 2026-10-18 — Events kept 90 days in full, then summaries and costs — user's choice.
- 2026-10-18 — Audit log of user actions — user's choice.
- 2026-10-18 — A security assessment screen per project, with estimated and actual cost and summarized findings — user's request.
- 2026-10-18 — Security: dynamic tests on an app started in the worktree with Docker, isolated network — user's choice.
- 2026-10-18 — Fix tasks and re-tests from findings in the first version — user's choice.
- 2026-10-18 — Optimizer as an ordinary task, no dedicated screen — user's choice.
- 2026-10-18 — Live updates over SSE with Last-Event-ID replay — server-to-client traffic, replay for free.
- 2026-10-18 — RFC 9457 errors, cursor pagination, `/api/v1` — user's confirmation.
- 2026-10-18 — Email and password login, owner-created accounts — user's choice (a).
- 2026-10-18 — GitHub App with polling for testing, webhooks in production — user's choice; the server sits behind a VPN while testing.
- 2026-10-18 — Testing on one server behind a VPN; a hosting provider to be chosen for production — user's choice.
- 2026-10-18 — Android first, iOS later — user's choice.
- 2026-10-18 — Non-functional defaults (English, WCAG 2.2 AA, <2 s log latency, 1 per role / 3 total, 60 min per step, daily backups) — user's confirmation.
- 2026-10-18 — Claude subscription kept as a provider type marked "check the terms"; API key recommended — user's confirmation.
- 2026-10-18 — Dense web UI, airy mobile UI — user's choice.
- 2026-10-18 — Role avatars with one color each; sparing gradient; subtle motion — user's confirmation.
- 2026-10-18 — No 2FA in the first version — user's choice.
- 2026-10-18 — Studio is the first product feature (M1), after the foundations — user's choice.
- 2026-10-18 — Each feature spec covers web and mobile together — user's choice.
- 2026-10-18 — Roadmap kept in this file only, no GitHub issues yet — user's choice.
- 2026-10-18 — Fixed agent roles (the six of this template) — user's choice; configurable roles later, if ever.

## Open questions
- (none)
