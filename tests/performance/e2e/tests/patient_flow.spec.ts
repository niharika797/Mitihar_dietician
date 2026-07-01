/**
 * Patient app E2E — targets Expo web build at http://localhost:8081
 *
 * Prerequisites:
 *   cd mitihar-patient-app && pnpm start  (runs Metro + Expo web)
 *   OR: pnpm expo export --platform web && serve dist/
 *
 * If Expo web is not running, these tests are automatically skipped.
 * Patient flows are the primary target for Expo Go on-device testing.
 *
 * Playwright project config: baseURL = http://localhost:8081
 */

import { test, expect } from '@playwright/test';

const PATIENT_EMAIL = 'testpatient001@mityahar.test';
const PATIENT_PASSWORD = 'TestPat@2026';

async function isExpoWebRunning(page: Parameters<typeof test>[1] extends (arg: any) => any ? never : any): Promise<boolean> {
  try {
    const r = await page.request.get('http://localhost:8081');
    return r.status() < 500;
  } catch {
    return false;
  }
}

test.describe('Patient App Flows (Expo Web)', () => {
  test.beforeAll(async ({ browser }) => {
    const page = await browser.newPage();
    const up = await isExpoWebRunning(page);
    await page.close();
    if (!up) {
      // Mark all tests in this suite as skipped
      test.skip(true as any, 'Expo web not running at localhost:8081 — start with: cd mitihar-patient-app && pnpm start');
    }
  });

  test('Patient sees meal plan within 3 seconds', async ({ page }) => {
    const t0 = Date.now();

    // Navigate to patient app
    await page.goto('/');
    await page.waitForLoadState('networkidle', { timeout: 15_000 });

    // Login — Expo Router auth flow: /login or /(auth)/login
    const emailInput = page.locator('input[placeholder*="email" i], input[name="email"]').first();
    await emailInput.waitFor({ timeout: 10_000 });
    await emailInput.fill(PATIENT_EMAIL);

    const passInput = page.locator('input[placeholder*="password" i], input[name="password"]').first();
    await passInput.fill(PATIENT_PASSWORD);

    const loginBtn = page.getByRole('button', { name: /login|sign in/i }).first();
    await loginBtn.click();

    // Wait for tabs or home screen
    await page.waitForURL('**/(tabs)/**', { timeout: 15_000 }).catch(() => {
      // Expo web may not change URL — just wait for tab bar
    });

    const totalLoginMs = Date.now() - t0;
    console.log(`  Login + navigation: ${totalLoginMs}ms`);

    // Navigate to Meals tab
    const mealTab = page.getByRole('tab', { name: /meal|food|plan/i })
      .or(page.locator('[href*="meal"], [href*="plan"]'));
    if (await mealTab.count() > 0) {
      await mealTab.click();
    }

    // Verify combo cards render
    const comboCard = page.locator('[class*="combo"], [class*="meal-card"], [data-testid="combo-card"]').first();
    await expect(comboCard).toBeVisible({ timeout: 5000 });

    // Verify kcal values shown
    const kcalText = page.locator('text=/\\d+\\s*(kcal|cal)/i').first();
    await expect(kcalText).toBeVisible({ timeout: 3000 });

    const totalMs = Date.now() - t0;
    console.log(`  Total (login → meals tab → combo visible): ${totalMs}ms`);
    expect(totalMs, 'Meal plan must render within 3 seconds of login').toBeLessThan(3000);
  });

  test('Progress tab loads today data', async ({ page }) => {
    // Login
    await page.goto('/');
    await page.waitForLoadState('networkidle', { timeout: 15_000 });

    const emailInput = page.locator('input[placeholder*="email" i], input[name="email"]').first();
    await emailInput.waitFor({ timeout: 10_000 });
    await emailInput.fill(PATIENT_EMAIL);
    await page.locator('input[placeholder*="password" i], input[name="password"]').first().fill(PATIENT_PASSWORD);
    await page.getByRole('button', { name: /login|sign in/i }).first().click();
    await page.waitForLoadState('networkidle', { timeout: 10_000 });

    // Navigate to progress tab
    const progressTab = page.getByRole('tab', { name: /progress|track/i })
      .or(page.locator('[href*="progress"]'));
    if (await progressTab.count() === 0) {
      test.skip(true as any, 'Progress tab not found in Expo web navigation');
      return;
    }

    const t = Date.now();
    await progressTab.click();
    // Verify today's date or a progress chart/ring renders
    const progressEl = page.locator('[class*="progress"], [class*="chart"], [data-testid="progress"]').first();
    await expect(progressEl).toBeVisible({ timeout: 5000 });
    console.log(`  Progress tab render: ${Date.now() - t}ms`);
  });
});
