import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  globalSetup: "./tests/global-setup.ts",
  timeout: 60_000,
  retries: 0,
  use: {
    baseURL: "http://localhost:8081",
    // storageState is written by globalSetup before tests run.
    // Playwright injects localStorage entries at context creation time,
    // so every test starts already authenticated — no login UI needed.
    storageState: "tests/storageState.json",
    browserName: "chromium",
    headless: true,
    viewport: { width: 390, height: 844 },
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], viewport: { width: 390, height: 844 } },
    },
  ],
});
