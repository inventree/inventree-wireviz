import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { viteExternalsPlugin } from 'vite-plugin-externals'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react({
      jsxRuntime: 'classic'
    }),
    viteExternalsPlugin({
      react: 'React',
      'react-dom': 'ReactDOM',
      '@mantine/core': 'MantineCore',
      "@mantine/notifications": 'MantineNotifications',
    }),
  ],
  esbuild: {
    jsx: 'preserve',
  },
  build: {
    cssCodeSplit: false,
    manifest: false,
    rollupOptions: {
      preserveEntrySignatures: "exports-only",
      input: [
        './src/WirevizPanel.tsx',
        './src/WirevizSettings.tsx',
        './src/WirevizDashboard.tsx',
      ],
      output: {
        dir: '../inventree_wireviz/static',
        entryFileNames: '[name].js',
        assetFileNames: 'assets/[name].[ext]',
        globals: {
          react: 'React',
          'react-dom': 'ReactDOM',
          '@mantine/core': 'MantineCore',
          "@mantine/notifications": 'MantineNotifications',
        },
      },
      external: ['react', 'react-dom', '@mantine/core', '@mantine/notifications'],
    }
  },
  optimizeDeps: {
    exclude: ['react', 'react-dom', '@mantine/core', '@mantine/notifications'],
  },
})
