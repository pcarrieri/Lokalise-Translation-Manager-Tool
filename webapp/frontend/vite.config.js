import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173, // <--- forza sempre questa porta
    strictPort: true // <--- fallisce se è occupata (meglio per debugging)
  }
})
