import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  build: {
    outDir: '../frappe_whatsapp/public/frontend',
    emptyOutDir: true,
    rollupOptions: {
      input: './index.html',
    },
  },
  server: {
    port: 8080,
    proxy: {
      '^/(app|api|assets|files)': {
        target: 'http://dev.localhost:8000',
        ws: true,
        router: function (req) {
          const site_name = req.headers.host.split(':')[0];
          return `http://${site_name}:8000`;
        },
      },
    },
  },
})
