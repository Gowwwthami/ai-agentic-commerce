import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // SPA fallback: serve index.html for all unknown routes in dev
    historyApiFallback: true,
  },
  preview: {
    // SPA fallback for vite preview
    historyApiFallback: true,
  },
  appType: 'spa',
})
