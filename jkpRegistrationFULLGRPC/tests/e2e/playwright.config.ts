import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: '.',
  timeout: 30_000,
  retries: 0,
  use: {
    baseURL: 'http://localhost:5175',
    headless: true,
    viewport: { width: 1280, height: 900 },
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: 'VITE_GRPC_URL=http://localhost:8080 bun run dev -- --port 5175',
    cwd: '../../client',
    port: 5175,
    reuseExistingServer: true,
  },
})
