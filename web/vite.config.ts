import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Only proxy API routes — exclude the SPA route /interview/:id
      '^/interview/(start|[^/]+/(answer|arbitrate|status|report|stream))': {
        target: 'http://localhost:8765',
        changeOrigin: true,
      },
    },
  },
})
