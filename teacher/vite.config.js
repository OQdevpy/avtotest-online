// vite.config.js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  base: './',
  server: {
    host: '0.0.0.0', // Set host to 0.0.0.0
    port: 5173,      // Specify the port
    // Faqat `npm run dev` uchun — /api va /media shu backendga proxy qilinadi
    // (VITE_API_URL=/api/v1 bilan ishlatiladi, qarang: ../dev.sh).
    proxy: {
      '/api': { target: process.env.DEV_BACKEND_URL || 'http://127.0.0.1:9005', changeOrigin: true },
      '/media': { target: process.env.DEV_BACKEND_URL || 'http://127.0.0.1:9005', changeOrigin: true },
    },
    watch: {
      ignored: ['**/C:/hiberfil.sys', '**/C:/pagefile.sys'],  // Ignore system files
    },
  },
  plugins: [react()],
  build: {
    outDir: 'dist',
    rollupOptions: {
      input: {
        main: 'index.html'
      }
    }
  },
  resolve: {
    alias: {
        '@api': '/src/api/proxy'
    }
},
// public/ → dist/: static-images, Electron uchun main.cjs va preload.cjs
publicDir: 'public',
});
