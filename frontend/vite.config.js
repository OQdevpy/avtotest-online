// vite.config.js
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  base: './',
  server: {
    host: '0.0.0.0', // Set host to 0.0.0.0
    port: 5173,      // Specify the port
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
publicDir: '/src/assets/',
});
