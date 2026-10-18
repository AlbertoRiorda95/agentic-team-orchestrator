/** @type {import('tailwindcss').Config} */
module.exports = {
  // The app is dark-only. With the default 'media' mode, NativeWind on web throws when it
  // syncs the <html> class with the color scheme.
  darkMode: 'class',
  content: ['./app/**/*.{ts,tsx}', './components/**/*.{ts,tsx}'],
  // The theme (colors, spacing, type scale...) comes from the shared design tokens.
  presets: [require('nativewind/preset'), require('@devorchestrator/tokens/tailwind-preset')],
};
