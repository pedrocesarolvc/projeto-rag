import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Em produção (Docker), o FastAPI serve o build (dist/) direto —
// mesma origem, sem CORS, sem proxy. Em dev (`npm run dev`), o proxy
// abaixo manda as chamadas de API para o backend rodando à parte
// (`uvicorn app.main:app`, porta 8000).
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/documentos': 'http://localhost:8000',
      '/perguntas': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
