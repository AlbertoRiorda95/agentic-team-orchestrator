/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  // The theme (colors, spacing, type scale...) comes from the shared design tokens.
  presets: [require('nativewind/preset'), require('@devorchestrator/tokens/tailwind-preset')],
};
