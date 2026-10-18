---
name: foundations-review-patterns
description: Recurring frontend mistakes seen in the status page review (mobile vs web parity, focus, line height) to anticipate in later reviews
metadata:
  type: project
---

Seen in the foundations status-page review (2026-10-18):
- Mobile misses things the web gets free from CSS inheritance: line height
  (`leading-body`), safe area insets. Check both on every mobile screen.
- Disabled-while-loading buttons drop keyboard focus; prefer `aria-disabled`.
- Web and mobile must render the same asset crop; check for wrapper parity.
- The designer session may lack browser/shell tools: say so and mark items "(verify)".
- Border color uses `fg-subtle` until a `border` token is proposed (with `auth-and-users`).
