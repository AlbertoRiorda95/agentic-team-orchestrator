// apps/web/e2e/status.spec.ts: the status page in its five states (foundations
// spec, "Screens and states"), at 320, 768 and 1280 px. The readiness API is
// mocked with page.route(), so every state is reachable without a backend.
import { test, expect, type Page } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const READY = '**/api/v1/health/ready';
const ok = { status: 'ok', checks: { database: 'ok' }, version: '0.1.0+abc1234' };

type State = { name: string; mock: (page: Page) => Promise<void>; settled: boolean };

const states: State[] = [
  {
    name: 'success',
    settled: true,
    mock: (p) => p.route(READY, (r) => r.fulfill({ status: 200, json: ok })),
  },
  {
    name: 'degraded',
    settled: true,
    mock: (p) =>
      p.route(READY, (r) => r.fulfill({ status: 200, json: { ...ok, status: 'degraded' } })),
  },
  {
    name: 'error',
    settled: true,
    mock: (p) =>
      p.route(READY, (r) =>
        r.fulfill({
          status: 503,
          json: { status: 'down', checks: { database: 'failed' }, version: '0.1.0' },
        }),
      ),
  },
  {
    name: 'unreachable',
    settled: true,
    mock: (p) => p.route(READY, (r) => r.abort('connectionrefused')),
  },
  // the request never answers: the page stays in its loading state
  {
    name: 'loading',
    settled: false,
    mock: (p) => p.route(READY, () => new Promise<void>(() => {})),
  },
];

for (const s of states) {
  test(`status page, ${s.name}: layout, accessibility, screenshot`, async ({ page }, info) => {
    await s.mock(page);
    await page.goto('/');
    if (s.settled) await page.waitForLoadState('networkidle');
    else await page.waitForTimeout(500);

    await page.screenshot({ path: info.outputPath(`status-${s.name}.png`), fullPage: true });

    // soft checks: every problem is reported in one run
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - window.innerWidth,
    );
    expect.soft(overflow, 'horizontal scroll in px').toBeLessThanOrEqual(0);

    const axe = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
    expect
      .soft(
        axe.violations.map((v) => `${v.id}: ${v.help}`),
        'accessibility (axe)',
      )
      .toEqual([]);

    if (info.project.use.hasTouch) {
      const small = await page.$$eval('button, [role=button]', (els) =>
        els
          .filter((e) => {
            const r = e.getBoundingClientRect();
            return r.width > 0 && (r.width < 44 || r.height < 44);
          })
          .map((e) => e.outerHTML.slice(0, 80)),
      );
      expect.soft(small, 'touch targets under 44 px').toEqual([]);
    }

    // "Check again" is the only focusable element: its ring must be visible,
    // also while a re-check is running (the review asked to keep it focusable)
    await page.keyboard.press('Tab');
    const focus = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement | null;
      if (!el || el === document.body) return 'nothing focusable';
      const cs = getComputedStyle(el);
      return cs.outlineStyle !== 'none' || cs.boxShadow !== 'none' ? 'visible' : 'invisible';
    });
    expect.soft(focus, 'keyboard focus').not.toBe('invisible');
  });
}
