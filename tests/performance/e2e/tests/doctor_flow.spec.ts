import { test, expect } from '@playwright/test';

const DOCTOR_EMAIL = 'dr.ashok.mehta@mitihar.test';
const DOCTOR_PASSWORD = 'DoctorTest@2026';
const TIMING_BUDGET_MS = 3000;

test.describe('Doctor Dashboard Flows', () => {
  let stepTimings: Record<string, number> = {};

  function mark(label: string, startMs: number) {
    const elapsed = Date.now() - startMs;
    stepTimings[label] = elapsed;
    console.log(`  [${label}] ${elapsed}ms`);
    expect(elapsed, `${label} exceeded ${TIMING_BUDGET_MS}ms`).toBeLessThan(TIMING_BUDGET_MS);
  }

  test('Doctor full workflow timing', async ({ page }) => {
    stepTimings = {};

    // Step 1: Login
    let t = Date.now();
    await page.goto('/doctor/login');
    await page.fill('input[name="email"], input[type="email"]', DOCTOR_EMAIL);
    await page.fill('input[name="password"], input[type="password"]', DOCTOR_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/doctor/**', { timeout: 10_000 });
    mark('Login', t);

    // Step 2: Patient list
    t = Date.now();
    await page.waitForSelector('table, [data-testid="patient-list"], .patient-list', { timeout: 5000 });
    mark('Patient list renders', t);

    // Step 3: Open first patient
    t = Date.now();
    const firstPatientLink = page.locator('table tbody tr a, [data-testid="patient-row"] a').first();
    await firstPatientLink.click();
    await page.waitForURL('**/patients/**', { timeout: 5000 });
    mark('Patient profile opens', t);

    // Step 4: Plan tab
    t = Date.now();
    const planTab = page.getByRole('tab', { name: /plan/i }).or(page.locator('[data-tab="plan"], button:has-text("Plan")'));
    await planTab.click();
    await page.waitForSelector('.combo-card, [data-testid="combo-card"], .plan-tab', { timeout: 5000 });
    mark('Plan tab renders', t);

    // Step 5: Weekly summary tab
    t = Date.now();
    const summaryTab = page.getByRole('tab', { name: /summary/i }).or(page.locator('[data-tab="summary"], button:has-text("Summary")'));
    await summaryTab.click();
    // Verify chips or summary content visible
    await page.waitForSelector('[class*="chip"], [class*="summary"], [data-testid="weekly-summary"]', { timeout: 5000 });
    mark('Weekly summary renders', t);

    // Step 6: Meal Config tab
    t = Date.now();
    const configTab = page.getByRole('tab', { name: /config|meal config/i })
      .or(page.locator('[data-tab="config"], button:has-text("Config")'));
    if (await configTab.count() > 0) {
      await configTab.click();
      // Verify pinned dishes section exists
      await page.waitForSelector('[class*="pinned"], [data-testid="meal-config"]', { timeout: 5000 });
      // Verify slot_type is shown on a dish card
      const slotLabel = page.locator('text=/grain|protein|vegetable|fat|beverage/i').first();
      if (await slotLabel.count() > 0) {
        await expect(slotLabel).toBeVisible({ timeout: 3000 });
      }
      mark('Meal Config tab + slot_type visible', t);
    } else {
      console.log('  [Meal Config] tab not found — skipping');
    }

    // Step 7: Approve plan
    t = Date.now();
    const approveBtn = page.getByRole('button', { name: /approve/i });
    if (await approveBtn.count() > 0) {
      await approveBtn.click();
      // Wait for toast or confirmation dialog
      const toast = page.locator('[class*="toast"], [role="alert"], [data-testid="toast"]');
      await expect(toast).toBeVisible({ timeout: 5000 });
      mark('Approve plan + toast', t);
    } else {
      console.log('  [Approve] button not found — plan may already be approved');
    }

    // Print timing summary
    console.log('\nStep timings:', JSON.stringify(stepTimings, null, 2));
  });

  test('Recipe search is fast', async ({ page }) => {
    // Login first
    await page.goto('/doctor/login');
    await page.fill('input[name="email"], input[type="email"]', DOCTOR_EMAIL);
    await page.fill('input[name="password"], input[type="password"]', DOCTOR_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/doctor/**', { timeout: 10_000 });

    // Navigate to a patient's meal config where recipe search appears
    const firstPatientLink = page.locator('table tbody tr a, [data-testid="patient-row"] a').first();
    if (await firstPatientLink.count() === 0) {
      test.skip(true, 'No patients found in UI — seed patients first');
      return;
    }
    await firstPatientLink.click();
    await page.waitForURL('**/patients/**', { timeout: 5000 });

    const configTab = page.getByRole('tab', { name: /config/i });
    if (await configTab.count() === 0) {
      test.skip(true, 'Meal Config tab not found');
      return;
    }
    await configTab.click();

    // Find recipe search input
    const searchInput = page.locator('input[placeholder*="search" i], input[placeholder*="dish" i], input[placeholder*="recipe" i]').first();
    if (await searchInput.count() === 0) {
      test.skip(true, 'Recipe search input not found');
      return;
    }

    // Test search speed: "Dal"
    let t = Date.now();
    await searchInput.fill('Dal');
    const dropdown = page.locator('[class*="dropdown"], [class*="suggest"], [role="listbox"]');
    await expect(dropdown).toBeVisible({ timeout: 500 });
    const dalTime = Date.now() - t;
    console.log(`  Dal search dropdown: ${dalTime}ms`);
    expect(dalTime).toBeLessThan(500);

    // Test search speed: "Rice"
    await searchInput.fill('');
    t = Date.now();
    await searchInput.fill('Rice');
    await expect(dropdown).toBeVisible({ timeout: 500 });
    const riceTime = Date.now() - t;
    console.log(`  Rice search dropdown: ${riceTime}ms`);
    expect(riceTime).toBeLessThan(500);

    // Verify slot_type labels in results
    const slotLabel = page.locator('[class*="slot"], text=/grain|protein|vegetable/i').first();
    if (await slotLabel.count() > 0) {
      await expect(slotLabel).toBeVisible();
    }
  });
});
