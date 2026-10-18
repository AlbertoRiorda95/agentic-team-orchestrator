# Design studio

An interactive design session between the user and the designer. Use it for
the project design (`docs/design/project.md`) and for every new feature or
redesign. It is the only place where large design decisions are made; tasks
only implement what a ready spec says.

Start it with `/design-studio <feature>` (Claude Code), or ask:
"run a design studio session for <feature> following docs/roles/design-studio.md".

## Rules
- You are the designer (`docs/roles/designer.md`). You write specs, never code.
- Read first: `AGENTS.md`, `docs/design/project.md`, the existing specs, the
  design-system skill, the API contract in `docs/api/`.
- Ask, propose, iterate. At most five questions per round. When there is a
  real choice, offer two or three options with their trade-offs and a
  recommendation.
- Keep a running draft in `docs/design/<feature>.md` from
  `docs/design/_spec-template.md`, and update it after every round, so the
  session can stop and resume at any time.
- Write decisions, not the conversation: the spec says what was decided and
  why in one line, not how the discussion went.
- Do not mark the spec `ready: yes` while the readiness checklist has open
  items or "Open questions" is not empty.

## Rounds
1. **Goal.** Who the users are, what they need to achieve, what success
   looks like, what is out of scope.
2. **Flows.** The main user flows, step by step; edge cases and errors.
3. **Screens.** Pages and components, their states (empty, loading, error,
   success), responsive behavior, accessibility.
4. **Data and API.** Entities and fields the feature needs, the endpoints
   and their shapes. Draft the changes to `docs/api/` in the spec; backend
   applies them.
5. **Breakdown.** The implementation tasks: role, what, depends on, and
   whether they can run as one team task.
6. **Readiness.** Walk the checklist with the user; resolve or record every
   open question.

## When the spec is ready
1. Set `ready: yes` and the date.
2. Commit the spec (and nothing else) on a branch `design/<feature>`, and
   open a merge request titled "design: <feature>". Locally without a
   remote, just commit.
3. Tell the user which tasks to create from the breakdown, or, with the
   orchestrator, that it will create them after the merge.
