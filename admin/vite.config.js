import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  // Faqat `npm run dev` uchun — /api va /media shu backendga proxy qilinadi.
  const devBackend = env.DEV_BACKEND_URL || 'http://127.0.0.1:9005';

  return {
    plugins: [
      react(),
      tailwindcss(),
    ],
    server: {
      port: 5174,
      host: '0.0.0.0',
      proxy: {
        '/api': {
          target: devBackend,
          changeOrigin: true,
          secure: false,
        },
        '/media': {
          target: devBackend,
          changeOrigin: true,
          secure: false,
        },
      },
    },
  };
});
