/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { TanStackRouterVite } from '@tanstack/router-vite-plugin';
import path from 'node:path';

export default defineConfig({
  plugins: [
    // TanStack Router MUST come before JSX-transforming plugins — it introspects
    // JSX to discover route definitions. See plugin error if order is swapped.
    TanStackRouterVite({ target: 'react', autoCodeSplitting: true }),
    react(),
  ],
  // T-122: Vite по умолчанию ищет .env в корне проекта (apps/frontend), но
  // ключ Яндекс.Карт и VITE_MAP_IMPL живут в КОРНЕВОМ .env — там же, откуда их
  // читают backend (pydantic-settings) и docker compose (build-args). Один
  // источник правды вместо дублирования ключа в apps/frontend/.env.local.
  // В Docker путь ведёт в / (там .env нет) — переменные приходят из build-args.
  envDir: path.resolve(__dirname, '../..'),
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@/generated': path.resolve(__dirname, './src/generated'),
      '@/components': path.resolve(__dirname, './src/components'),
      '@/api': path.resolve(__dirname, './src/api'),
    },
  },
  server: {
    port: 5173,
    strictPort: false,
    host: '0.0.0.0',
    proxy: {
      // Проксируем API запросы в backend (для dev)
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    sourcemap: true,
    target: 'es2022',
    rollupOptions: {
      output: {
        manualChunks: {
          react: ['react', 'react-dom'],
          query: ['@tanstack/react-query'],
          router: ['@tanstack/react-router'],
          table: ['@tanstack/react-table', '@tanstack/react-virtual'],
          charts: ['recharts'],
          maps: ['leaflet', 'react-leaflet'],
        },
      },
    },
  },
});
