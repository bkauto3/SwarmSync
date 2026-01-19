import { dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

import { defineConfig, devices } from '@playwright/test';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const baseURL = process.env.E2E_BASE_URL ?? 'http://localhost:3000';
const shouldRunSmoke = process.env.RUN_STRIPE_SMOKE === '1' || process.env.RUN_STRIPE_SMOKE === 'true';

export default defineConfig({
  testDir: './tests',
  timeout: 120_000,
  expect: {
    timeout: 15_000,
  },
  use: {
    baseURL,
    headless: true,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: process.env.E2E_BASE_URL
    ? undefined
    : {
        command: 'npm run dev',
        cwd: __dirname,
        port: 3000,
        timeout: 120_000,
        reuseExistingServer: !process.env.CI,
      },
  // Prevent accidental runs on CI unless explicitly requested.
  grep: shouldRunSmoke ? undefined : /skip_stripe_smoke/,
});

