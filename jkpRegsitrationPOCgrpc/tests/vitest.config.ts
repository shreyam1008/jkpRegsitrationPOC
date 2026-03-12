import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'node:path'

const clientDir = path.resolve(__dirname, '../client')

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      react: path.resolve(__dirname, 'node_modules/react'),
      'react-dom': path.resolve(__dirname, 'node_modules/react-dom'),
      'react-router': path.resolve(__dirname, 'node_modules/react-router'),
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./setup.ts'],
    include: ['unit/**/*.test.{ts,tsx}'],
    deps: {
      optimizer: {
        web: {
          include: ['react', 'react-dom', 'react-router'],
        },
      },
    },
  },
})
