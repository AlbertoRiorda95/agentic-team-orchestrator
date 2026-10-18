/**
 * Design tokens: the single source of truth for web and mobile.
 * Values come from the design-system tables (docs/design, design-system skill).
 * `tokens.css` and `tailwind-preset.cjs` are generated from this file
 * (`npm run gen:tokens`): never edit them by hand.
 */

export const colors = {
  bg: '#111B30',
  'bg-deep': '#0D1832',
  surface: '#12234B',
  fg: '#F4F5FA',
  'fg-muted': '#A5ACBF',
  'fg-subtle': '#8A93AB',
  primary: '#2D5DF8',
  'primary-foreground': '#FFFFFF',
  'primary-fg': '#5B82FA',
  'accent-cyan': '#03BBFB',
  'accent-indigo': '#484AF7',
  'accent-violet': '#6B38F9',
  'accent-violet-text': '#8B6BFB',
  success: '#03CB99',
  warning: '#F5A524',
  danger: '#F04461',
  navy: '#091E48',
} as const;

export const gradients = {
  brand: { from: colors.primary, to: colors['accent-violet'] },
} as const;

/** Agent role colors: always shown together with the role name. */
export const roleColors = {
  designer: '#8B6BFB',
  frontend: '#03BBFB',
  backend: '#03CB99',
  devops: '#5B82FA',
  optimizer: '#F5A524',
  security: '#F04461',
} as const;

/** Agent and task states: never shown by color alone (icon or label too). */
export const stateColors = {
  idle: colors['fg-subtle'],
  running: colors['accent-cyan'],
  'waiting-for-review': colors['primary-fg'],
  blocked: colors.warning,
  failed: colors.danger,
  done: colors.success,
} as const;

export const fontFamily = {
  sans: 'Inter',
  mono: 'JetBrains Mono',
} as const;

/**
 * Font files by weight. React Native has no weight axis for custom fonts, so each
 * weight is a separate family (`native`, the name registered with expo-font).
 */
export const fontFaces = [
  { key: 'sans', family: 'Inter', weight: 400, native: 'Inter_400Regular' },
  { key: 'sans-medium', family: 'Inter', weight: 500, native: 'Inter_500Medium' },
  { key: 'sans-semibold', family: 'Inter', weight: 600, native: 'Inter_600SemiBold' },
  { key: 'sans-bold', family: 'Inter', weight: 700, native: 'Inter_700Bold' },
  { key: 'mono', family: 'JetBrains Mono', weight: 400, native: 'JetBrainsMono_400Regular' },
  {
    key: 'mono-medium',
    family: 'JetBrains Mono',
    weight: 500,
    native: 'JetBrainsMono_500Medium',
  },
] as const;

/** px */
export const fontSize = {
  xs: 12,
  sm: 14,
  base: 16,
  lg: 18,
  xl: 20,
  '2xl': 24,
  '3xl': 30,
  '4xl': 36,
} as const;

export const fontWeight = {
  normal: 400,
  medium: 500,
  semibold: 600,
  bold: 700,
} as const;

export const lineHeight = {
  body: 1.5,
  heading: 1.2,
} as const;

/** px, on a 4 px scale; keys follow the Tailwind spacing names. */
export const spacing = {
  0: 0,
  1: 4,
  2: 8,
  3: 12,
  4: 16,
  6: 24,
  8: 32,
  12: 48,
} as const;

/** px */
export const radius = {
  sm: 6,
  md: 10,
  lg: 16,
  full: 9999,
} as const;

/** px, web only */
export const breakpoints = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
} as const;

/** px: max width of single-column pages (status page, login screen). */
export const layout = {
  narrow: 480,
} as const;

/** ms, never above 200. */
export const motion = {
  fast: 120,
  base: 200,
} as const;

export type ColorToken = keyof typeof colors;
export type RoleColorToken = keyof typeof roleColors;
export type StateColorToken = keyof typeof stateColors;
