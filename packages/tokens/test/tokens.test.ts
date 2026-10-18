import { describe, expect, it } from 'vitest';
import { colors, motion, spacing } from '../src/tokens.ts';

function luminance(hex: string): number {
  const channels = [1, 3, 5].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  const [r, g, b] = channels as [number, number, number];
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (hi + 0.05) / (lo + 0.05);
}

describe('color tokens', () => {
  // Ratios documented in the design system (docs/design, design-system skill).
  it.each([
    ['fg', 'bg', 15.8],
    ['fg-muted', 'bg', 7.6],
    ['fg-subtle', 'bg', 5.6],
    ['primary-foreground', 'primary', 5.2],
    ['primary-fg', 'bg', 4.9],
    ['accent-cyan', 'bg', 7.8],
    ['accent-violet-text', 'bg', 4.6],
    ['danger', 'bg', 4.7],
  ] as const)('%s on %s has about %s:1 contrast', (fg, bg, documented) => {
    expect(contrast(colors[fg], colors[bg])).toBeCloseTo(documented, 0);
  });

  it('keeps the state icons above 3:1 on the background', () => {
    for (const name of ['success', 'warning', 'danger', 'accent-cyan', 'fg-subtle'] as const) {
      expect(contrast(colors[name], colors.bg)).toBeGreaterThanOrEqual(3);
    }
  });
});

describe('other tokens', () => {
  it('keeps motion at or under 200 ms', () => {
    for (const ms of Object.values(motion)) expect(ms).toBeLessThanOrEqual(200);
  });

  it('keeps spacing on the 4 px scale', () => {
    for (const value of Object.values(spacing)) expect(value % 4).toBe(0);
  });
});
