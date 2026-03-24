import { defineConfig } from 'vitest/config'
import { resolve } from 'path'

export default defineConfig({
  resolve: {
    alias: {
      '@client': resolve(__dirname, '../../client/src'),
    },
  },
  test: {
    include: ['frontend/**/*.test.ts'],
    root: resolve(__dirname, '..'),
  },
})
