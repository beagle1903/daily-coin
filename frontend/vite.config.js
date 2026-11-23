import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // The browser calls relative /api paths; forward them to the backend.
    // Override the target with DAILY_COIN_API_TARGET if the API is elsewhere.
    proxy: {
      '/api': process.env.DAILY_COIN_API_TARGET || 'http://127.0.0.1:8000',
    },
    host: true,
    port: 5173,
    strictPort: true,
    watch: {
      usePolling: process.env.CHOKIDAR_USEPOLLING === 'true',
    },
  },
})
