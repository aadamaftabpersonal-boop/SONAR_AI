import { defineConfig, devices } from '@playwright/test'

// Runs against an already-running Sonar (API + web app). Nothing here starts servers, so the test
// exercises exactly what a judge would see. See README.md in this folder.
export default defineConfig({
  testDir: '.',
  timeout: 120_000,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: process.env.SONAR_WEB_URL ?? 'http://localhost:5173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    { name: 'desktop', use: { viewport: { width: 1280, height: 800 } } },
    { name: 'phone', use: { ...devices['iPhone 13'] } },
  ],
})
