# DevOrchestrator mobile app

Expo (Expo Router) app. From the repository root: `npm run start -w apps/mobile`
(dev server on port 8081).

## Environment variables

Expo reads `.env` from `apps/mobile`, **not** from the repository root. Create
`apps/mobile/.env` to change a value, and restart the dev server afterwards. Only
variables prefixed with `EXPO_PUBLIC_` reach the app.

| Variable              | Default                        | Use                  |
| --------------------- | ------------------------------ | -------------------- |
| `EXPO_PUBLIC_API_URL` | `http://localhost:8000/api/v1` | Base URL of the API. |

On a physical device or an emulator `localhost` is the device itself: use the
machine's LAN address (Android emulator: `http://10.0.2.2:8000/api/v1`).
