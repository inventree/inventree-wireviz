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
        './src/WirevizPanel.tsx',
        './src/WirevizSettings.tsx',
      ],
      output: {
        dir: '../inventree_wireviz/static',
        entryFileNames: '[name].js',
        assetFileNames: 'assets/[name].[ext]',
      },
      }
  }
})
