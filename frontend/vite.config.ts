import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'node:url';

// URL pública por defecto para el og:image de index.html (antes
// `metadataBase` en el layout de Next). En producción se pasa VITE_APP_URL.
process.env.VITE_APP_URL ??= 'http://localhost:3000';

// Vite (dev server + build) y Vitest comparten esta config.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./', import.meta.url)),
    },
  },
  server: {
    // 3000 dentro del contenedor; docker-compose lo publica en 3100 (V2).
    host: true,
    port: 3000,
    strictPort: true,
  },
  preview: {
    host: true,
    port: 3000,
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./tests/setup.ts'],
    globals: true,
    include: [
      'tests/unit/**/*.test.{ts,tsx}',
      // pruebas junto al código en lib/, app/, components/ y hooks/
      'lib/**/*.test.{ts,tsx}',
      'app/**/*.test.{ts,tsx}',
      'components/**/*.test.{ts,tsx}',
      'hooks/**/*.test.{ts,tsx}',
    ],
    coverage: {
      provider: 'v8',
      include: ['lib/**', 'components/**', 'hooks/**', 'app/**'],
      exclude: ['**/*.test.{ts,tsx}', '**/*.d.ts'],
    },
  },
});
