import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173, // чтобы совпадало с тем, что в телеге
    host: true, // чтобы было доступно извне
  },
})