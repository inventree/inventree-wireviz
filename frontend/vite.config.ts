import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { viteExternalsPlugin } from 'vite-plugin-externals'

/**
 * The following libraries are externalized to avoid bundling them with the plugin.
 * These libraries are expected to be provided by the InvenTree core application.
 */
export const externalLibs : Record<string, string> = {
  react: 'React',
  'react-dom': 'ReactDOM',
  'ReactDom': 'ReactDOM',
  '@mantine/core': 'MantineCore',
  "@mantine/notifications": 'MantineNotifications',
};

// Just the keys of the externalLibs object
const externalKeys = Object.keys(externalLibs);

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react({
      jsxRuntime: 'classic'
    }),
    viteExternalsPlugin(externalLibs),
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
          globals: externalLibs
        },
        {
          dir: '../inventree_wireviz/static',
          entryFileNames: '[name]-[hash].min.js',
          assetFileNames: 'assets/[name].[ext]',
          globals: externalLibs
        }
      ],
      external: externalKeys,
    }
  },
  optimizeDeps: {
    exclude: externalKeys,
  },
})
