---
name: design-system
description: DevOrchestrator's tokens, components and visual rules (dark theme, web and mobile). Use it for every interface spec or page.
---

# DevOrchestrator design system

Dark theme only. Brand assets: `docs/design/brand/` (logo, app icon, typography).

## Where the tokens live
`packages/tokens`: TypeScript values, plus a generated `tokens.css` (web) and a shared
Tailwind preset used by the web app (Tailwind v4) and the mobile app (NativeWind).
Never hand-written color, spacing or typography values.

## Color
| Token | Value | Use |
|---|---|---|
| `bg` | `#111B30` | app background |
| `bg-deep` | `#0D1832` | sidebars, inset areas |
| `surface` | `#12234B` | cards, panels, modals |
| `fg` | `#F4F5FA` | body text (15.8:1 on `bg`) |
| `fg-muted` | `#A5ACBF` | secondary text (7.6:1) |
| `fg-subtle` | `#8A93AB` | captions, placeholders (5.6:1) |
| `primary` | `#2D5DF8` | filled primary buttons, with `#FFFFFF` text (5.2:1) |
| `primary-fg` | `#5B82FA` | links and primary text on `bg` (4.9:1); not on `surface` |
| `accent-cyan` | `#03BBFB` | highlights, focus ring (7.8:1) |
| `accent-indigo` | `#484AF7` | gradient midpoint, decoration only |
| `accent-violet` | `#6B38F9` | decoration only; as text use `#8B6BFB` (4.6:1 on `bg`) |
| `success` | `#03CB99` | brand green, success |
| `warning` | `#F5A524` | warnings, blocked |
| `danger` | `#F04461` | errors, destructive actions |
| `navy` | `#091E48` | wordmark on light backgrounds (marketing only) |
| `gradient-brand` | `#2D5DF8 → #6B38F9` | see Character |

Agent roles: each has an avatar in the logo's style (round head, two eyes) and a color,
always shown with the role name: designer `#8B6BFB`, frontend `#03BBFB`, backend
`#03CB99`, devops `#5B82FA`, optimizer `#F5A524`, security `#F04461`.

Agent and task states: idle `fg-subtle`, running `accent-cyan`, waiting for review
`primary-fg`, blocked `warning`, failed `danger`, done `success`. A state is never
shown by color alone: always an icon or label too.

## Character
- Web: a dense developer tool (Linear, GitHub, Vercel): compact rows (32–36 px),
  much information per screen, keyboard shortcuts.
- Mobile: airy: cards, comfortable rows (at least 44 px), one main action per screen.
- Gradient only on the logo, the login screen and the main call to action of empty
  states; solid colors everywhere else.
- Motion: subtle, under 200 ms (pulse on `running`, new log lines fading in); none
  with reduced motion.

## Typography
- `font-sans`: **Inter** (UI). `font-mono`: **JetBrains Mono** (logs, diffs, IDs, code).
- Scale (px): 12, 14 (body small), 16 (body), 18, 20, 24, 30, 36. Weights 400, 500, 600, 700.
- Line height 1.5 for body text, 1.2 for headings.

## Spacing, radius, breakpoints
- Spacing on a 4 px scale: `1`=4, `2`=8, `3`=12, `4`=16, `6`=24, `8`=32, `12`=48.
- Radius: `sm` 6, `md` 10, `lg` 16, `full` (the app icon uses about 22% of its size).
- Breakpoints (web): `sm` 640, `md` 768, `lg` 1024, `xl` 1280.

## Base components
- Web: **shadcn/ui** (Radix + Tailwind), copied into `apps/web`, themed from the tokens.
- Mobile: **React Native Reusables** + **NativeWind**, with the same component names
  and props as on the web where possible.
- Set: Button, IconButton, TextField, Select, Checkbox, Switch, Card, Badge
  (agent state), Avatar (agent), Tabs, Modal or Sheet, Toast, Table (web), List
  (mobile), LogViewer (mono). Each has default, hover/pressed, visible focus,
  disabled and error states.

## Rules
- Minimum contrast 4.5:1 for body text, 3:1 for large text and UI borders.
- Touch targets of at least 44 px (mobile and touch web).
- Every page has empty, loading and error states.
- Visible focus: a 2 px `accent-cyan` ring. Respect reduced-motion settings.
