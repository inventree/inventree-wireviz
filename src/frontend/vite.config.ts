import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    cssCodeSplit: false,
    manifest: false,
    rollupOptions: {
      preserveEntrySignatures: "exports-only",
      input: [
        './src/main.tsx',
        './src/WirevizPanel.tsx'
      ],
      output: {
        entryFileNames: 'static/[name].js',
        assetFileNames: 'static/assets/[name].[ext]',
      },
      }
  }
})
