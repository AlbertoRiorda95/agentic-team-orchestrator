import type { ExpoConfig } from 'expo/config';
const appIcon = '../../packages/tokens/assets/app-icon.png';

// Expo loads this file with Node, which cannot run the TypeScript source of
// @devorchestrator/tokens (`as const` fails to parse). So the color is repeated here:
// keep it equal to `colors.bg` in packages/tokens/src/tokens.ts.
const colors = { bg: '#111B30' };

// Static colors of the native shell (splash screen, adaptive icon).
const config: ExpoConfig = {
  name: 'DevOrchestrator',
  slug: 'devorchestrator',
  scheme: 'devorchestrator',
  version: '0.1.0',
  orientation: 'portrait',
  userInterfaceStyle: 'dark',
  backgroundColor: colors.bg,
  icon: appIcon,
  platforms: ['android', 'web'],
  android: {
    package: 'dev.devorchestrator.app',
    adaptiveIcon: { foregroundImage: appIcon, backgroundColor: colors.bg },
  },
  web: { bundler: 'metro', output: 'single' },
  plugins: [
    'expo-router',
    'expo-font',
    [
      'expo-splash-screen',
      { image: appIcon, imageWidth: 200, resizeMode: 'contain', backgroundColor: colors.bg },
    ],
    'expo-status-bar',
  ],
  experiments: { typedRoutes: true },
};

export default config;
