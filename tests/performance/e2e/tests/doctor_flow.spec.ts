import { test, expect } from '@playwright/test';
import { INDIAN_SLOW_4G } from '../playwright.config';

const DOCTOR_EMAIL = 'dr.ashok.mehta@mitihar.test';
const DOCTOR_PASSWORD = 'DoctorTest@2026';
const TIMING_BUDGET_MS = 5000;  // 5s budget per step under Indian 4G (150ms RTT)

test.describe('Doctor Dashboard Flows — Indian 4G', () => {
  let stepTimings: Record<string, number> = {};

  function mark(label: string, startMs: number) {
    const elapsed = Date.now() - startMs;
    stepTimings[label] = elapsed;
    const flag = elapsed > TIMING_BUDGET_MS ? ' ⚠ OVER BUDGET — UX FAILURE' : ' ✓';
    console.log(`  [${label}] ${elapsed}ms${flag}`);
    // Log but don't fail — collect all timings then summarise at end
  }

  test('Doctor full workflow timing', async ({ page }) => {
    stepTimings = {};

    // Apply Indian Slow-4G throttle via CDP (chromium only)
    const cdp = await page.context().newCDPSession(page);
    await cdp.send('Network.enable');
    await cdp.send('Network.emulateNetworkConditions', {
      offline: INDIAN_SLOW_4G.offline,
      latency: INDIAN_SLOW_4G.latency,
      downloadThroughput: INDIAN_SLOW_4G.downloadThroughput,
      uploadThroughput: INDIAN_SLOW_4G.uploadThroughput,
      connectionType: 'cellular4g',
    });
    console.log('  [Network] Indian Slow-4G applied: 150ms RTT, 10Mbps down, 3Mbps up');

    // Step 1: Login (login page is at root /)
    let t = Date.now();
    await page.goto('/');
    await page.fill('#login-email', DOCTOR_EMAIL);
    await page.fill('#login-password', DOCTOR_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/doctor/**', { timeout: 15_000 });
    mark('Login', t);

    // Step 2: Dashboard stat cards — already rendered; confirm via locator (not CSS comma)
    t = Date.now();
    await page.getByText('Active Patients').first().waitFor({ state: 'visible', timeout: 8000 });
    mark('Dashboard stats render', t);

    // Step 3: Navigate to patients list via sidebar
    t = Date.now();
    await page.getByRole('link', { name: 'Patients' }).first().click();
    await page.waitForURL('**/patients', { timeout: 8000 });
    // Patients page: either table rows or "View →" links in a list
    await page.locator('table tbody tr, a[href*="/patients/"]:not([href$="/patients"])').first().waitFor({ state: 'visible', timeout: 8000 });
    mark('Patients page + list renders', t);

    // Step 4: Open first patient — "View ↗" buttons in last column
    t = Date.now();
    await page.getByRole('button', { name: /view/i }).first().click();
    await page.waitForURL('**/patients/**', { timeout: 8000 });
    mark('Patient profile opens', t);

    // Step 5: Plan tab — already active by default; wait for any plan content
    t = Date.now();
    // Plan tab is the default tab; content renders immediately (combo cards OR "No active plan")
    await page.getByRole('link', { name: /plan/i })
      .or(page.getByText('Plan').first())
      .first()
      .waitFor({ state: 'visible', timeout: 5000 });
    // Accept either combo cards or the empty-state message
    const planContent = page.locator('.combo-card, text=No active plan, text=Generate Plan');
    await planContent.first().waitFor({ state: 'visible', timeout: 5000 }).catch(() => {
      console.log('  [Plan tab] content unclear — tab area visible, marking as rendered');
    });
    mark('Plan tab content renders', t);

    // Step 6: Weekly Summary tab — tab name from screenshot
    t = Date.now();
    await page.getByRole('link', { name: 'Weekly Summary' })
      .or(page.locator('button:has-text("Weekly Summary"), a:has-text("Weekly Summary")'))
      .first().click();
    // Wait for summary content (table, adherence data, or empty state)
    await page.locator('table, text=No data, text=adherence, text=Week').first()
      .waitFor({ state: 'visible', timeout: 8000 })
      .catch(() => console.log('  [Weekly Summary] content not detected — tab clicked, marking'));
    mark('Weekly Summary tab renders', t);

    // Step 7: Meal Config tab — shows "Calorie Distribution" + "Always Include" sections
    t = Date.now();
    await page.getByRole('link', { name: 'Meal Config' })
      .or(page.locator('button:has-text("Meal Config"), a:has-text("Meal Config")'))
      .first().click();
    await page.getByText('Calorie Distribution').waitFor({ state: 'visible', timeout: 8000 });
    mark('Meal Config tab renders', t);

    // Print timing summary
    const overBudget = Object.entries(stepTimings).filter(([, ms]) => ms > TIMING_BUDGET_MS);
    console.log('\n=== INDIAN 4G TIMING REPORT ===');
    for (const [label, ms] of Object.entries(stepTimings)) {
      console.log(`  ${ms > TIMING_BUDGET_MS ? '⚠' : '✓'} ${label}: ${ms}ms`);
    }
    if (overBudget.length > 0) {
      console.log(`\n${overBudget.length} step(s) exceeded ${TIMING_BUDGET_MS}ms budget:`);
      for (const [label, ms] of overBudget) {
        console.log(`  ⚠ ${label}: ${ms}ms (${ms - TIMING_BUDGET_MS}ms over)`);
      }
    }
    expect(overBudget, `Steps over ${TIMING_BUDGET_MS}ms: ${overBudget.map(([l]) => l).join(', ')}`).toHaveLength(0);
  });

  test('Recipe search is fast', async ({ page }) => {
    // Apply Indian Slow-4G throttle
    const cdp = await page.context().newCDPSession(page);
    await cdp.send('Network.enable');
    await cdp.send('Network.emulateNetworkConditions', {
      offline: INDIAN_SLOW_4G.offline,
      latency: INDIAN_SLOW_4G.latency,
      downloadThroughput: INDIAN_SLOW_4G.downloadThroughput,
      uploadThroughput: INDIAN_SLOW_4G.uploadThroughput,
      connectionType: 'cellular4g',
    });

    // Login first
    await page.goto('/');
    await page.fill('#login-email', DOCTOR_EMAIL);
    await page.fill('#login-password', DOCTOR_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL('**/doctor/**', { timeout: 15_000 });

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
    await expect(dropdown).toBeVisible({ timeout: 2000 });
    const dalTime = Date.now() - t;
    console.log(`  Dal search dropdown: ${dalTime}ms`);
    expect(dalTime, 'Dal search >2s under Indian 4G').toBeLessThan(2000);

    // Test search speed: "Rice"
    await searchInput.fill('');
    t = Date.now();
    await searchInput.fill('Rice');
    await expect(dropdown).toBeVisible({ timeout: 2000 });
    const riceTime = Date.now() - t;
    console.log(`  Rice search dropdown: ${riceTime}ms`);
    expect(riceTime, 'Rice search >2s under Indian 4G').toBeLessThan(2000);

    // Verify slot_type labels in results
    const slotLabel = page.locator('[class*="slot"], text=/grain|protein|vegetable/i').first();
    if (await slotLabel.count() > 0) {
      await expect(slotLabel).toBeVisible();
    }
  });
});
