import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The proxy is only for `npm run dev` against a locally running API
// (uvicorn on :8000). In Docker, nginx does this same job.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
