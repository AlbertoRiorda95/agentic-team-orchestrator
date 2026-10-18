import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';

const root = fileURLToPath(new URL('.', import.meta.url));
const repoRoot = fileURLToPath(new URL('../..', import.meta.url));
const pkg = JSON.parse(readFileSync(new URL('./package.json', import.meta.url), 'utf8')) as {
  version: string;
};

export default defineConfig(({ mode }) => {
  // VITE_API_PROXY_TARGET comes from the environment or from a .env at the repo root.
  const env = loadEnv(mode, repoRoot, 'VITE_');
  const target = process.env.VITE_API_PROXY_TARGET ?? env.VITE_API_PROXY_TARGET;

  return {
    plugins: [react(), tailwindcss()],
    define: { __APP_VERSION__: JSON.stringify(pkg.version) },
    resolve: { alias: { '@': `${root}src` } },
    server: {
      port: 5173,
      proxy: { '/api': { target: target ?? 'http://localhost:8000', changeOrigin: true } },
    },
    test: {
      environment: 'jsdom',
      setupFiles: ['./src/test/setup.ts'],
      css: false,
    },
  };
});
