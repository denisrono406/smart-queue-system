import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    port: 5000,
    proxy: {
      '/': {
        target: 'http://127.0.0.1:5001',
        changeOrigin: true,
        ws: true,
      },
    },
  },
});
