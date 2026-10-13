import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 真实开发轨工程形态（frontend-foundation.md §2.5，P0-06）：
// - 去 vite-plugin-singlefile：恢复正常 dev/build，不再追求 file:// 单文件直开
//   （单文件演示形态随 fork 留在 teach-petro-agent/prototype/app）；
// - dev 期 /api 走 vite proxy → FastAPI :8000，前端代码只认同源相对路径
//   （api/client.js 的 API_BASE 默认 '/api'）。
export default defineConfig({
  plugins: [react()],
  base: '/',
  server: {
    port: 5173,
    proxy: {
      // V2 后端（:8001）——须排在 '/api' 之前（前缀匹配先到先得）。
      '/api/v2': {
        target: 'http://localhost:8001',
        changeOrigin: true
      },
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    chunkSizeWarningLimit: 1500
  }
})
