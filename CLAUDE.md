@AGENTS.md

# Claude Code-only notes

- The agents live in `.claude/agents/`; each one points to its prompt in `docs/roles/`.
- Delegate by file boundary, as in AGENTS.md. Explicitly: `@designer`, `@backend`...
- optimizer and security are on-demand roles: never delegate to them unless the
  user asks in this conversation.
- After every delegation, check `docs/alignment/` for entries with `status: open`
  (the alignment-check hook reminds you). Handle them as AGENTS.md says:
  designer first, then the affected roles, then mark the entry resolved. Ask the
  user only when designer sets `decision-needed: yes`.
- Preloaded skills are declared in each agent's `skills:` field. The on-demand ones
  (web-design-guidelines, webapp-testing, security-review, diagnosing-bugs,
  github-actions-templates) are used when the role prompt says so.
- Between tasks: `/clear`. On long sessions: `/compact`.
