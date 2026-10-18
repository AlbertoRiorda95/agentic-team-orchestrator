/**
 * Generates `tokens.css` and `tailwind-preset.cjs` from `src/tokens.ts`, and copies
 * the brand assets from `docs/design/brand/` into `assets/`.
 *
 * `node scripts/generate.ts`          writes the files
 * `node scripts/generate.ts --check`  exits 1 when a committed file is out of date (CI)
 */
import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  breakpoints,
  colors,
  fontFamily,
  fontSize,
  fontWeight,
  fontFaces,
  gradients,
  layout,
  lineHeight,
  motion,
  radius,
  roleColors,
  spacing,
  stateColors,
} from '../src/tokens.ts';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const brandDir = join(root, '..', '..', 'docs', 'design', 'brand');
const check = process.argv.includes('--check');

const header = (comment: [string, string]) =>
  `${comment[0]} Generated from src/tokens.ts by scripts/generate.ts. Do not edit by hand. ${comment[1]}\n`;

const px = (n: number) => `${n}px`;
const entries = <T extends object>(o: T) => Object.entries(o) as [string, string | number][];

const fontStack = {
  sans: `"${fontFamily.sans}", ui-sans-serif, system-ui, sans-serif`,
  mono: `"${fontFamily.mono}", ui-monospace, SFMono-Regular, monospace`,
};

function css(): string {
  const lines: string[] = [];
  for (const [k, v] of entries(colors)) lines.push(`--color-${k}: ${v};`);
  for (const [k, v] of entries(roleColors)) lines.push(`--role-${k}: ${v};`);
  for (const [k, v] of entries(stateColors)) lines.push(`--state-${k}: ${v};`);
  lines.push(
    `--gradient-brand: linear-gradient(135deg, ${gradients.brand.from}, ${gradients.brand.to});`,
  );
  lines.push(`--font-sans: ${fontStack.sans};`, `--font-mono: ${fontStack.mono};`);
  for (const [k, v] of entries(fontSize)) lines.push(`--text-${k}: ${px(Number(v))};`);
  for (const [k, v] of entries(fontWeight)) lines.push(`--font-weight-${k}: ${v};`);
  for (const [k, v] of entries(lineHeight)) lines.push(`--leading-${k}: ${v};`);
  for (const [k, v] of entries(spacing)) lines.push(`--space-${k}: ${px(Number(v))};`);
  for (const [k, v] of entries(radius)) lines.push(`--radius-${k}: ${px(Number(v))};`);
  for (const [k, v] of entries(breakpoints)) lines.push(`--breakpoint-${k}: ${px(Number(v))};`);
  for (const [k, v] of entries(layout)) lines.push(`--layout-${k}: ${px(Number(v))};`);
  for (const [k, v] of entries(motion)) lines.push(`--duration-${k}: ${v}ms;`);
  return `${header(['/*', '*/'])}\n:root {\n${lines.map((l) => `  ${l}`).join('\n')}\n}\n`;
}

const mapPx = (o: object) =>
  Object.fromEntries(entries(o).map(([k, v]) => [k, px(Number(v))]));

function preset(): string {
  // Tailwind 3 format: NativeWind 4 (mobile) reads it directly, Tailwind 4 (web)
  // loads it with `@config`.
  const nativeFamilies = Object.fromEntries(
    fontFaces.map((f) => [`native-${f.key}`, [f.native]]),
  );
  const theme = {
    colors: { transparent: 'transparent', current: 'currentColor', ...colors },
    spacing: mapPx(spacing),
    borderRadius: mapPx(radius),
    screens: mapPx(breakpoints),
    fontFamily: {
      sans: fontStack.sans.split(', '),
      mono: fontStack.mono.split(', '),
      ...nativeFamilies,
    },
    fontSize: mapPx(fontSize),
    fontWeight: Object.fromEntries(entries(fontWeight).map(([k, v]) => [k, String(v)])),
    lineHeight: Object.fromEntries(entries(lineHeight).map(([k, v]) => [k, String(v)])),
    transitionDuration: { DEFAULT: `${motion.base}ms`, ...Object.fromEntries(entries(motion).map(([k, v]) => [k, `${v}ms`])) },
    extend: {
      maxWidth: mapPx(layout),
      minHeight: { touch: px(44) },
      minWidth: { touch: px(44) },
      backgroundImage: {
        'gradient-brand': `linear-gradient(135deg, ${gradients.brand.from}, ${gradients.brand.to})`,
      },
    },
  };
  return `${header(['//', ''])}\n/** @type {import('tailwindcss').Config} */\nmodule.exports = {\n  theme: ${JSON.stringify(theme, null, 2).replace(/\n/g, '\n  ')},\n};\n`;
}

const outputs: Record<string, string> = {
  'tokens.css': css(),
  'tailwind-preset.cjs': preset(),
};
const assets = ['logo.png', 'app-icon.png'];

let stale = false;
for (const [name, content] of Object.entries(outputs)) {
  const file = join(root, name);
  const current = existsSync(file) ? readFileSync(file, 'utf8') : null;
  if (current === content) continue;
  if (check) {
    console.error(`${name} is out of date`);
    stale = true;
  } else {
    writeFileSync(file, content);
    console.log(`wrote ${name}`);
  }
}
mkdirSync(join(root, 'assets'), { recursive: true });
for (const name of assets) {
  const from = join(brandDir, name);
  const to = join(root, 'assets', name);
  const same = existsSync(to) && readFileSync(from).equals(readFileSync(to));
  if (same) continue;
  if (check) {
    console.error(`assets/${name} is out of date`);
    stale = true;
  } else {
    copyFileSync(from, to);
    console.log(`copied assets/${name}`);
  }
}
if (stale) {
  console.error("Run 'npm run gen:tokens' and commit the result.");
  process.exit(1);
}
