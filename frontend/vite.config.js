import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/chat': 'http://localhost:8080',
      '/chats': 'http://localhost:8080',
      '/documents': 'http://localhost:8080',
      '/stats': 'http://localhost:8080',
      '/health': 'http://localhost:8080',
    }
  }
})