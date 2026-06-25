import { chromium, FullConfig } from "@playwright/test";
import * as fs from "fs";
import * as path from "path";

async function globalSetup(_config: FullConfig) {
  // Step 1: Get fresh JWT from backend (form-encoded, same as OAuth2PasswordRequestForm)
  const res = await fetch("http://localhost:8001/api/v1/auth/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      username: "priya.test@mityahar.com",
      password: "Test@1234",
    }).toString(),
  });
  if (!res.ok) {
    throw new Error(`[global-setup] Login failed: ${res.status} ${await res.text()}`);
  }
  const { access_token, refresh_token } = (await res.json()) as {
    access_token: string;
    refresh_token: string;
  };
  console.log("[global-setup] JWT acquired.");

  // Step 2: Write storageState.json — Playwright injects this into localStorage
  // before each test context is created. On web, expo-secure-store falls back to
  // localStorage using keys mitihar_access_token / mitihar_refresh_token.
  const storageStatePath = path.resolve("tests/storageState.json");
  fs.writeFileSync(
    storageStatePath,
    JSON.stringify({
      cookies: [],
      origins: [
        {
          origin: "http://localhost:8081",
          localStorage: [
            { name: "mitihar_access_token", value: access_token },
            { name: "mitihar_refresh_token", value: refresh_token },
          ],
        },
      ],
    })
  );
  console.log("[global-setup] storageState.json written.");

  // Step 3: Pre-warm the Expo Metro bundle.
  // First request triggers compilation (30-90s). Subsequent test pages hit the
  // Metro cache and load in <5s. Running this once here prevents per-test timeouts.
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    storageState: storageStatePath,
    viewport: { width: 390, height: 844 },
  });
  const page = await context.newPage();
  try {
    await page.goto("http://localhost:8081/meals");
    await page.waitForSelector("text=BREAKFAST", { timeout: 120_000 });
    console.log("[global-setup] Expo bundle pre-warm complete — BREAKFAST visible.");
  } catch (e) {
    console.warn(`[global-setup] Pre-warm timed out (${e}). Tests may be slow on first load.`);
  }
  await browser.close();
}

export default globalSetup;
