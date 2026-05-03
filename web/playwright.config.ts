import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests-e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  timeout: 120000,
  reporter: [['html', { open: 'never' }], ['list']],
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command: 'cd .. && python3 -m uvicorn src.api.main:create_app --host 0.0.0.0 --port 8765 --factory',
      url: 'http://localhost:8765/docs',
      timeout: 30000,
      reuseExistingServer: true,
    },
    {
      command: 'npm run dev',
      url: 'http://localhost:5173',
      timeout: 30000,
      reuseExistingServer: true,
    },
  ],
});
