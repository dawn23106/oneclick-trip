import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ command }) => ({
  // 生产环境由 api-trip.yjzdev.cn/admin/ 提供静态页面；
  // 本地开发仍保持 http://127.0.0.1:5174/，不改变原调试入口。
  base: command === 'build' ? '/admin/' : '/',
  plugins: [vue()],
  server: {
    host: '127.0.0.1',
    port: 5174,
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true
      }
    }
  }
}))
