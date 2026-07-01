import { defineConfig } from '@playwright/test';

/**
 * Indian Slow-4G network profile.
 * Apply per-test: await page.emulateNetworkConditions(INDIAN_SLOW_4G)
 * `offline` is the only property BrowserContextOptions exposes directly;
 * latency + throughput require CDP and must be set via emulateNetworkConditions.
 */
export const INDIAN_SLOW_4G = {
  offline: false,
  latency: 150,                                // 150 ms RTT
  downloadThroughput: (10 * 1024 * 1024) / 8, // 10 Mbps in bytes/s
  uploadThroughput: (3 * 1024 * 1024) / 8,    // 3 Mbps in bytes/s
};

export default defineConfig({
  testDir: './tests',
  timeout: 60_000,
  use: {
    baseURL: 'http://localhost:5173',
    browserName: 'chromium',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    trace: 'on-first-retry',
  },
  reporter: [['html', { outputFolder: '../reports/playwright-report', open: 'never' }]],
  projects: [
    {
      name: 'Doctor Dashboard',
      use: { baseURL: 'http://localhost:5173' },
      testMatch: 'doctor_flow.spec.ts',
    },
    {
      name: 'Patient App (Expo Web)',
      use: { baseURL: 'http://localhost:8081' },
      testMatch: 'patient_flow.spec.ts',
    },
  ],
});
