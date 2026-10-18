const preset = require('jest-expo/jest-preset');

/** @type {import('jest').Config} */
module.exports = {
  ...preset,
  setupFilesAfterEnv: [...(preset.setupFilesAfterEnv ?? []), '<rootDir>/test/setup.ts'],
  // lucide-react-native ships ESM (.mjs) for React Native: transform it like the rest.
  transform: { ...preset.transform, '\\.mjs$': 'babel-jest' },
  transformIgnorePatterns: [
    'node_modules/(?!((jest-)?react-native|@react-native(-community)?)|expo(nent)?|@expo(nent)?/.*|@expo-google-fonts/.*|react-navigation|@react-navigation/.*|react-native-svg|lucide-react-native|@rn-primitives/.*|nativewind|react-native-css-interop)',
  ],
};
