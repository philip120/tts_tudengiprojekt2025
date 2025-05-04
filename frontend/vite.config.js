import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  root: '.',
  base: './', // Use relative paths for assets
  build: {
    outDir: 'dist', // Output directory for build files
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html'), // Ensure index.html is included in the build
      },
    },
  },
})
