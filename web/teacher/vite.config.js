// Avtotest web (o'qituvchi) — brauzerda ochiladigan versiya.
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  // Nisbiy yo'llar: sayt istalgan manzilda (domen ildizi yoki /web/...) ochiladi
  base: './',
  server: {
    host: '0.0.0.0',
    port: 5185,
    // Faqat `npm run dev` uchun — /api va /media shu backendga proxy qilinadi
    // (VITE_API_URL=/api/v1 bilan ishlatiladi).
    proxy: {
      '/api': { target: process.env.DEV_BACKEND_URL || 'http://127.0.0.1:9005', changeOrigin: true },
      '/media': { target: process.env.DEV_BACKEND_URL || 'http://127.0.0.1:9005', changeOrigin: true },
    },
  },
  plugins: [react()],
  build: {
    outDir: 'dist',
    // Manba kodi (source map) build'ga qo'shilmaydi
    sourcemap: false,
  },
  publicDir: 'public',
});
