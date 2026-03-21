import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  use: {
    baseURL: 'http://localhost:5174',
    headless: true,
  },
  webServer: [
    {
      command: 'cd ../server && PATH="$HOME/.local/bin:$PATH" uv run uvicorn app.main:app --port 8001',
      port: 8001,
      reuseExistingServer: true,
    },
    {
      command: 'cd ../client && bun run dev --port 5174',
      port: 5174,
      reuseExistingServer: true,
    },
  ],
})
