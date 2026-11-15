import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  // The hosted demo lives under /<repo>/ on GitHub Pages (set VITE_BASE in the deploy workflow).
  base: process.env.VITE_BASE || '/',
  // Static demo mode bundles the saved results from ../data/samples.
  server: { fs: { allow: ['..'] } },
  // Leaflet + Geoman make one ~600 kB chunk; fine for a single-page hackathon demo.
  build: { chunkSizeWarningLimit: 800 },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
});
