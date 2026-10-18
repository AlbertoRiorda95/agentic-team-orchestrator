---
feature: foundations
ready: yes              # yes only when the checklist below is complete
updated: 2026-10-18
owner: designer
---

# Foundations

## Goal
For the team building DevOrchestrator (the agents and the user): a working,
empty monorepo where every command in AGENTS.md runs and CI is green, so every
later feature only adds code. Milestone M0, first of `foundations`,
`app-shell`, `auth-and-users`.

Success: on a fresh clone, `make install`, `make lint`, `make test`,
`make build`, `make openapi` and `npm run gen:api` succeed; `docker compose up`
starts API and Postgres; the web and mobile skeletons start, use the shared
tokens and fonts, and show the API readiness through the generated client; CI
is green, including a smoke test of the running stack.

## Out of scope
- Navigation, sidebar, tabs, login screen, keyboard shortcuts (`app-shell`).
- Authentication, users, `/me` (`auth-and-users`).
- Every domain table and endpoint other than `/health` and `/health/ready`.
- The shadcn/ui and React Native Reusables component set beyond what the
  status page uses (Button, Badge); the rest comes with the features that need it.
- Deployment, hosting, EAS builds, iOS, push notifications.

## User flows
Users here are developers (agents and the user) working in the repository.

1. **Set up a fresh clone.** `make install` → `docker compose up -d` (API on
   8000, Postgres on 5432; the API applies migrations at start) →
   `npm run dev -w apps/web` (5173) and `npx expo start` in `apps/mobile` (8081).
   Errors: a port is taken (compose fails with Docker's message; ports are
   documented in `.env.example`); Postgres not ready yet (the API waits for the
   `db` healthcheck before starting).
2. **Check the stack (status page).** Open the web app or the mobile app → the
   page requests `GET /api/v1/health/ready` → shows the readiness.
   Edge cases: API down or unreachable (network error) → "API unreachable" with
   the URL tried and a Retry button; database down → API answers 503 with
   `status: down`, the page shows "Down" and the failed check; slow answer →
   loading state, request times out after 10 s and counts as unreachable.
   The page re-checks on window focus (web) and app foreground (mobile), and
   on Retry; no background polling.
3. **Change the API.** Backend changes the code → `make openapi` rewrites
   `docs/api/openapi.yaml` → `npm run gen:api` regenerates
   `packages/api-client` → a type mismatch breaks `npm run typecheck`.
   Errors: the committed contract differs from the export → CI fails with the
   message "run 'make openapi' and commit it".
4. **Open a PR.** CI runs install, lint, type checks, contract drift,
   migrations, build, tests, the mobile export, the compose smoke test, SBOM,
   licenses and vulnerabilities. Any red step fails the PR.

## Screens and states
One screen, the **status page**, on web (`apps/web`, route `/`) and mobile
(`apps/mobile`, Expo Router `app/index.tsx`). `app-shell` replaces it.

Layout, top to bottom, centered, on `bg` (no card: `danger` text does not
reach 4.5:1 on `surface`):
1. Logo (`docs/design/brand/logo.png`), 48 px (`12`), the only gradient on the page.
2. "DevOrchestrator", `font-sans` 24 / 600, `fg`. It is the page's `h1`.
3. Tagline "AI agents. Real software.", 14 / 400, `fg-muted`.
4. Status line: an icon in the state color + a label in `fg` (16 / 500).
5. Checks list (when the API answered): one row per entry of `checks`, name
   capitalized ("Database") in `fg-muted`, value as icon + "OK" / "Failed".
6. Versions, `font-mono` 12, `fg-subtle`: "API 0.1.0+abc1234 · Web 0.1.0"
   ("Mobile 0.1.0" on mobile); "API —" when unknown.
7. Button "Check again" (secondary on success; primary on error and
   unreachable).

| State | Status line | Checks | Button |
|---|---|---|---|
| loading (first load or re-check) | spinner icon in `fg-subtle` + "Checking the API…" | previous result kept on re-check, hidden on first load | disabled |
| success (`status: ok`) | check-circle in `success` + "All systems operational" | shown | "Check again", secondary |
| degraded (`status: degraded`, reserved for later checks) | alert-triangle in `warning` + "Degraded" | shown | "Check again", secondary |
| error (`503`, `status: down`) | x-circle in `danger` + "API is up, but not ready" | shown, failed rows first | "Check again", primary |
| unreachable (network error, timeout, unexpected response) | plug-off icon in `danger` + "API unreachable" and, below, the URL tried in `font-mono` 12 `fg-muted` | hidden | "Check again", primary |

There is no empty state: the page always has a result or a loading state.

Responsive behavior:
- Web: one centered column, max width `layout-narrow` (new token, 480 px),
  vertically centered from `md` up, top-aligned with `8` top padding below `md`;
  16 px (`4`) side gutter. Works from 320 px wide with no horizontal scroll.
- Mobile: same column, full width with `4` gutters, vertically centered in
  the safe area; button full width, at least 44 px tall.

Accessibility:
- The status line plus the checks list is one `role="status"`
  (`aria-live="polite"`) region, so screen readers hear the result after a
  re-check; on mobile `accessibilityLiveRegion="polite"` and
  `accessibilityRole="summary"` on the status line.
- Logo `alt="DevOrchestrator logo"`; icons are decorative (`aria-hidden`),
  the state is always in the label text.
- Focus order: "Check again" is the only focusable element; visible 2 px
  `accent-cyan` ring. The disabled button keeps its label; the busy state is
  announced by the live region.
- Contrast: labels in `fg` on `bg` (15.8:1); state icons ≥ 3:1 on `bg`
  (`danger` 4.7:1 is the lowest); versions in `fg-subtle` (5.6:1).
- Reduced motion: the spinner is replaced by a static clock icon.
- `<html lang="en">`; page `<title>` "DevOrchestrator".

Tokens: only from the design system (`packages/tokens`: color, typography,
spacing, radius, breakpoints, role colors, fonts). New tokens proposed here:
- `layout-narrow` = 480 px: max width of single-column pages (this page,
  then the login screen in `app-shell`).

Applies to: web and mobile, identical content; only the layout notes above differ.

### `packages/tokens` (both platforms)
- Source of truth: TypeScript values, exactly the tables of the
  design-system skill (colors, role colors, state colors, type scale, weights,
  line heights, spacing, radius, breakpoints, motion duration ≤ 200 ms) plus
  `layout-narrow`.
- Generated from it: `tokens.css` (CSS custom properties, web) and one shared
  Tailwind preset used by Tailwind v4 (web) and NativeWind (mobile). Generated
  files are rebuilt by a script and checked in CI (no hand edits).
- Fonts: Inter (400, 500, 600, 700) and JetBrains Mono (400, 500), self-hosted:
  `@fontsource` on web, `expo-font` on mobile; the app shows nothing until the
  fonts are loaded on mobile (splash screen kept), `font-display: swap` on web.
- Brand assets (logo, app icon) copied from `docs/design/brand/` into the
  package so both apps import them from one place; the mobile app icon and
  splash use the app icon on `bg`.

## Data and API
Entities and fields: none (no domain tables). Alembic is set up with an
empty baseline revision, so migrations run from the first commit.

Contract changes (applied by backend to `docs/api/`):
- Move the hand-written v0.1 contract to `docs/api/openapi-v0.1-design.yaml`,
  unchanged, with a header comment: design reference, not generated, not used
  by the clients. Later features export their part of it from FastAPI.
- `docs/api/openapi.yaml` becomes the FastAPI export (`make openapi`), with
  `info.version` 0.1.0 and server `http://localhost:8000/api/v1`. In
  foundations it holds two operations, as in v0.1:
  - `GET /health` (`operationId: health`, no auth): liveness, always `200`
    `{status: "ok", version}` while the process serves requests.
  - `GET /health/ready` (`operationId: readiness`, no auth): `200`
    `{status: "ok", checks: {database: "ok"}, version}`, or `503`
    `{status: "down", checks: {database: "failed"}, version}` when
    `SELECT 1` fails or takes more than 2 s.
- `Health` gets an optional `version: string`: the API package version, plus
  `+<short sha>` when `GIT_SHA` is set (compose and CI set it). Additive, not
  breaking.
- The RFC 9457 `application/problem+json` handler is installed for every
  error (404, 405, 422 with `errors[]`, 500), as the project conventions say.
- Update `docs/api/README.md`: the two files and their roles.

Interfaces other roles rely on (environment and ports):
| Variable | Used by | Default (local) |
|---|---|---|
| `DATABASE_URL` | API | `postgresql+asyncpg://postgres:postgres@localhost:5432/devorchestrator` |
| `CORS_ORIGINS` | API, comma separated | `http://localhost:8081` (Expo web) |
| `GIT_SHA` | API, optional | unset |
| `VITE_API_PROXY_TARGET` | web dev server: proxies `/api` | `http://localhost:8000` |
| `EXPO_PUBLIC_API_URL` | mobile | `http://localhost:8000/api/v1` (Android emulator: `http://10.0.2.2:8000/api/v1`; a device: the host's LAN or Tailscale address) |

All of them are listed in a root `.env.example`. The web app calls the
relative `/api/v1` (same origin, as in production); the mobile app calls
`EXPO_PUBLIC_API_URL`.

Breaking for existing clients: no (there are no clients yet).

## Acceptance criteria
- [ ] On a fresh clone with Docker, Node 24 and uv: `make install`,
      `make lint`, `make test`, `make build` succeed; `uv run --directory
      backend mypy` and `npm run typecheck` pass.
- [ ] `docker compose up -d` starts `api` and `db`; within 60 s
      `curl localhost:8000/api/v1/health/ready` returns `200` with
      `status: ok`, `checks.database: ok` and a `version`.
- [ ] With `docker compose stop db`, the same request returns `503` with
      `status: down` and `checks.database: failed` within 3 s.
- [ ] Any unknown path returns `404` with `Content-Type:
      application/problem+json`.
- [ ] `make openapi` on a clean tree leaves `git diff` empty;
      `docs/api/openapi.yaml` contains exactly `/health` and `/health/ready`;
      `docs/api/openapi-v0.1-design.yaml` is byte-identical to the previous
      `openapi.yaml` apart from the header comment.
- [ ] `npm run gen:api` regenerates `packages/api-client` with no diff; the
      web and mobile status pages call `readiness` through it (no hand-written
      response types).
- [ ] Web on `http://localhost:5173` and mobile on Expo web (`:8081`) and on
      the Android emulator show the status page in all five states of the
      table (degraded checked with a mocked response in tests).
- [ ] The page uses only `packages/tokens` values (no literal colors, sizes
      or font names in `apps/`), Inter and JetBrains Mono load with no request
      outside the app's origin.
- [ ] The page passes axe with no violations (web), has a visible focus ring
      on "Check again", touch target ≥ 44 px, and no horizontal scroll at 320 px.
- [ ] Unit tests: backend `/health` and `/health/ready` (ok and database
      failed); web (Vitest) and mobile (Jest) status page in loading,
      success, error and unreachable.
- [ ] CI on the PR is green, with a new compose smoke job that builds the
      image, starts the stack, waits for `/health/ready` = `ok` and tears it down.

## Decisions
- 2026-10-18 — The v0.1 hand-written contract moves to `docs/api/openapi-v0.1-design.yaml` (read-only reference); `docs/api/openapi.yaml` becomes the FastAPI export and grows feature by feature — keeps the CI drift check strict without stub routes.
- 2026-10-18 — Web and mobile skeletons show one status page (logo, name, API readiness through the generated client) — proves tokens, fonts, client and network end to end; `app-shell` replaces it.
- 2026-10-18 — `/health/ready` checks only the database in foundations — scheduler and runners are added when they exist (M2); the open `checks` map makes that non-breaking.
- 2026-10-18 — Inter and JetBrains Mono self-hosted (`@fontsource` on web, `expo-font` on mobile) — no third-party requests from a VPN-only tool.
- 2026-10-18 — `compose.yml` runs API + Postgres only; web and mobile dev servers run on the host — as AGENTS.md, fast reload.
- 2026-10-18 — Web reaches the API through a Vite proxy on `/api` (same origin, as in production); the API allows CORS from `CORS_ORIGINS` for Expo web — user's choice.
- 2026-10-18 — `Health` gets an optional `version` — tells which build is running; additive.
- 2026-10-18 — CI gets a compose smoke job — catches Dockerfile, startup migration and env breakage that unit tests miss.
- 2026-10-18 — The status page checks on load, on focus or foreground and on Retry; no polling — enough for a temporary page.
- 2026-10-18 — Status page sits on `bg` without a card — `danger` text fails 4.5:1 on `surface`.
- 2026-10-18 — New token `layout-narrow` (480 px) — single-column pages, reused by the login screen.
- 2026-10-18 — Tasks 1–3 run as one team task (backend, frontend, devops) — CI's contract step needs the Makefile, so a backend-only PR would be red; all new files keep the PR reviewable.

## Open questions
- (none)

## Review (task 4, 2026-10-18)
Scope: `apps/web/src/components/status-view.tsx`, `apps/mobile/components/status-view.tsx`,
the `ui/` Button and Badge of both apps, `packages/shared`, `packages/tokens`.

Method and limit: this round was a code review against the spec and the design
system. The designer session had no browser or shell tools, so the pages were NOT
opened at 320, 768 and 1280 px nor on Expo web. Items marked "(verify)" must be
checked by frontend in the browser before closing; a follow-up visual pass is
needed once someone can run the dev servers.

Matches the spec (no action): layout order, copy of the five states, state icons
and colors, `role="status"` and `aria-live` on web, `accessibilityRole="summary"`
and live region on mobile, decorative icons hidden, `lang` and `<title>`, reduced
motion swap (spinner to clock), failed rows first, "API —" fallback, 44 px button,
tokens only (no literal values in `apps/`), mobile fonts gate with the splash screen.

Feedback for frontend (task 5). Format as in the designer role; five items, the
most severe. Lower-priority findings are listed after.

- [IMPORTANT] apps/mobile/components/status-view.tsx:106-109 — the page is not
  placed in the safe area (no `SafeAreaView` or insets), so on a phone with a
  notch or a gesture bar the logo or the button can sit under system UI; the spec
  says "vertically centered in the safe area" — wrap in `SafeAreaView` from
  `react-native-safe-area-context` (or add `useSafeAreaInsets` to the content
  padding, `4`/`8` plus the inset) and keep `justify-center`.
- [IMPORTANT] apps/mobile/components/ui/text.tsx:18 and
  apps/mobile/components/status-view.tsx:119 — no line height is set anywhere on
  mobile (the web gets 1.5 from `body` in index.css; React Native has no
  inheritance), so body text uses the font's default and the `h1` is not 1.2 —
  add `leading-body` to the base `Text` class and `leading-heading` on the
  `h1` (the preset already exposes both).
- [IMPORTANT] apps/web/src/components/status-view.tsx:90-94 — the logo `img` has
  `scale-150` without a clipping wrapper (mobile has one), so it renders at 72 px
  instead of 48 px and bleeds out of its box, and the two apps show different
  logos (verify at 320 px) — wrap it in a `size-12 overflow-hidden rounded-md`
  element with the same crop as mobile and scale the image inside, or drop the
  crop if the result is acceptable at 48 px; both apps must render the same 48 px
  mark.
- [IMPORTANT] apps/web/src/components/status-view.tsx:112-119 — the button is
  `disabled` while loading, so a keyboard user who presses "Check again" loses
  focus (the browser moves it to `body`) and the 2 px focus ring disappears
  during the check — keep it focusable: `aria-disabled` plus ignoring `onClick`
  while loading, with the disabled look (`aria-disabled:opacity-60`,
  `aria-disabled:pointer-events-none`); same for mobile where a screen reader
  user gets the same effect (use `accessibilityState.busy` and keep `disabled`
  only for the visual if VoiceOver or TalkBack loses focus; verify).
- [NICE-TO-HAVE] apps/web/src/components/status-view.tsx:86 and
  apps/mobile/components/status-view.tsx:103 — `primary` is `false` while
  loading, so after an error the button flips from primary to secondary during
  the re-check and back again, a flicker on the one control the user is watching —
  keep the variant of the last result (`result?.kind`) while loading; use
  secondary only when there is no result yet.

Also found, not blocking (do them in the same round if cheap):
- Web check rows (status-view.tsx:67) are about 24 px high; the design system
  asks for compact 32 px rows on web: add `min-h-8`.
- Buttons use `transition-colors duration-fast`; add `motion-reduce:transition-none`.
- The "URL tried" line and the check rows disappear while loading, so the page
  jumps in height on every re-check; acceptable for now, revisit in `app-shell`.
- Add a test per state for the keyboard flow (focus stays on the button after
  activation) once the item above is fixed.

Decisions taken in this review (frontend additions to the tokens, from the
alignment entry `2026-10-18-3-frontend.md`):
- Accepted as part of the token set: `layout.touch` 44 px (`min-h-touch`),
  `primary-foreground` `#FFFFFF`, `accent-violet-text` `#8B6BFB`, `motion.fast`
  120 ms and `motion.base` 200 ms, and the per-weight native font families
  (`font-native-*`, mobile only). All of them restate values already in the design
  system, so no token is new in substance.
- Border: no border token for now. Secondary buttons and badges keep `fg-subtle`
  (5.6:1 on `bg`, above the 3:1 needed for UI borders). A real `border` token
  will be proposed with the first form (`auth-and-users`), where the field border
  needs to be seen on `surface` as well.
- Logo: `logo.png` has a light background and cannot sit on `bg`, so the page uses
  the app icon. Accepted as interim; the crop must be the same on both apps (item
  above). A transparent square mark in `docs/design/brand/` would replace the
  crop; it is a brand asset and is not produced in this task.

## Task breakdown
| # | Role | Task | Depends on |
|---|---|---|---|
| 1 | backend | `backend/`: uv project (Python 3.14, FastAPI, Pydantic v2, pydantic-settings, async SQLAlchemy 2.0, asyncpg, Alembic with empty baseline), `/api/v1` router, `/health` and `/health/ready` with `version`, RFC 9457 handler, CORS from `CORS_ORIGINS`, ruff + mypy + pytest config and tests, an export command for the contract; move v0.1 to `openapi-v0.1-design.yaml`, export the new `openapi.yaml`, update `docs/api/README.md` | — |
| 2 | frontend | Root `package.json` (workspaces, scripts `lint`, `typecheck`, `test`, `build`, `gen:api`), `tsconfig` base, ESLint + Prettier; `packages/tokens` (values, generated CSS and Tailwind preset, fonts, brand assets); `packages/api-client` (generated types + `openapi-fetch` client factory); `packages/shared` (readiness → page state mapping); `apps/web` (Vite, React 19, Tailwind v4, shadcn Button and Badge, status page, `/api` proxy, Vitest); `apps/mobile` (Expo Router, NativeWind, Reusables, `expo-font`, status page, Jest) | 1 (contract) |
| 3 | devops | Root `Makefile` (`install`, `lint`, `test`, `build`, `openapi`), `backend/Dockerfile` (uv, Python 3.14 slim, non-root, migrations then server, healthcheck on `/api/v1/health`), `.dockerignore`, `compose.yml` (`api` + `db` Postgres 17 with healthcheck, ports 8000 and 5432, `GIT_SHA`), root `.env.example`; CI: compose smoke job | 1, 2 |
| 4 | designer | Review the status page on web (320, 768, 1280 px) and mobile (Expo web at a phone viewport) in all states | 2 |
| 5 | frontend | Apply the review feedback | 4 |
| 6 | designer | `docs/design/project.md`, API surface: point to the contract split | 1 |

Team task possible: yes, and chosen for tasks 1–3 (roles: backend, frontend,
devops, in this order; one branch, one PR). Tasks 4–5 and 6 follow as separate
tasks once that PR is open.

## Readiness checklist
- [x] goal, users and out of scope agreed
- [x] every flow has its error and edge cases
- [x] every screen has empty, loading, error and success states
- [x] contract changes written, breaking changes approved by the user
- [x] acceptance criteria are observable
- [x] task breakdown with roles and dependencies
- [x] no open questions
