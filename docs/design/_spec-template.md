---
feature: <feature>
ready: no               # yes only when the checklist below is complete
updated: YYYY-MM-DD
owner: designer
---

# <Feature name>

## Goal
<who it is for, what they achieve, how we know it works>

## Out of scope
- ...

## User flows
1. ...

## Screens and states
| Screen / component | States | Notes |
|---|---|---|
| ... | empty, loading, error, success | ... |

Responsive behavior: ...
Accessibility: ...
Tokens: only from the design system; new tokens proposed here: ...

## Data and API
Entities and fields: ...
Contract changes (applied by backend to `docs/api/`):
- ...
Breaking for existing clients: no

## Acceptance criteria
- [ ] ...

## Decisions
- YYYY-MM-DD — <decision> — <one-line reason>

## Open questions
- (none)

## Task breakdown
| # | Role | Task | Depends on |
|---|---|---|---|
| 1 | backend | ... | — |
| 2 | frontend | ... | 1 |
Team task possible: yes / no (roles: ...)

## Readiness checklist
- [ ] goal, users and out of scope agreed
- [ ] every flow has its error and edge cases
- [ ] every screen has empty, loading, error and success states
- [ ] contract changes written, breaking changes approved by the user
- [ ] acceptance criteria are observable
- [ ] task breakdown with roles and dependencies
- [ ] no open questions
