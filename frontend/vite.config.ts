import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { viteExternalsPlugin } from 'vite-plugin-externals'

const globals = {
  react: 'React',
  'react-dom': 'ReactDOM',
  '@mantine/core': 'MantineCore',
  "@mantine/notifications": 'MantineNotifications',
};

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
    minify: true,
    manifest: true,
    sourcemap: true,
    cssCodeSplit: false,
    rollupOptions: {
      preserveEntrySignatures: "exports-only",
      input: [
        './src/WirevizPanel.tsx',
        './src/WirevizSettings.tsx',
        './src/WirevizDashboard.tsx',
      ],
      output: [
        {
          dir: '../inventree_wireviz/static',
          entryFileNames: '[name].js',
          assetFileNames: 'assets/[name].[ext]',
          globals: globals
        },
        {
          dir: '../inventree_wireviz/static',
          entryFileNames: '[name]-[hash].min.js',
          assetFileNames: 'assets/[name].[ext]',
          globals: globals
        }
      ],
      external: ['react', 'react-dom', '@mantine/core', '@mantine/notifications'],
    }
  },
  optimizeDeps: {
    exclude: ['react', 'react-dom', '@mantine/core', '@mantine/notifications'],
  },
})
