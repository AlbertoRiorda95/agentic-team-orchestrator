// jest-expo already mocks the native modules; the app config is not loaded in tests.
jest.mock('expo-constants', () => ({
  __esModule: true,
  default: { expoConfig: { version: '0.1.0' } },
}));
