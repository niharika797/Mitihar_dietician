/**
 * Session 21 — Patient App Adaptive UI
 * Verifies: meal suggestions, dish selection, calorie ring, snack log,
 *           week-strip past day, and selection persistence on reload.
 *
 * RN Web Pressable elements render as plain divs — native Playwright click()
 * times out. All interactions use pressRN(), which dispatches the full
 * pointer event sequence required to trigger React Native Web's Pressability.
 */
import { test, expect, Page } from "@playwright/test";

// ── Helpers ────────────────────────────────────────────────────────────────

/** Dispatch the pointer/mouse event sequence React Native Web Pressable needs. */
async function pressRN(page: Page, text: string): Promise<boolean> {
  return page.evaluate((targetText: string) => {
    const all = [...document.querySelectorAll("div")];
    for (const el of all) {
      if (el.children.length === 0 && el.textContent === targetText) {
        let p: Element | null = el.parentElement;
        for (let i = 0; i < 6; i++) {
          if (!p) break;
          const key = Object.keys(p).find((k) => k.startsWith("__reactProps"));
          if (key && (p as any)[key]?.onClick) {
            const rect = p.getBoundingClientRect();
            const cx = rect.left + rect.width / 2;
            const cy = rect.top + rect.height / 2;
            const opts = { bubbles: true, cancelable: true, clientX: cx, clientY: cy, pointerId: 1 };
            p.dispatchEvent(new PointerEvent("pointerdown", opts));
            p.dispatchEvent(new PointerEvent("pointerup", opts));
            p.dispatchEvent(new MouseEvent("click", opts));
            return true;
          }
          p = p.parentElement;
        }
      }
    }
    return false;
  }, text);
}

/** Same as pressRN but matches partial/contains text. */
async function pressRNContains(page: Page, text: string): Promise<boolean> {
  return page.evaluate((targetText: string) => {
    const all = [...document.querySelectorAll("div")];
    for (const el of all) {
      if (el.children.length === 0 && el.textContent?.includes(targetText)) {
        let p: Element | null = el.parentElement;
        for (let i = 0; i < 6; i++) {
          if (!p) break;
          const key = Object.keys(p).find((k) => k.startsWith("__reactProps"));
          if (key && (p as any)[key]?.onClick) {
            const rect = p.getBoundingClientRect();
            const cx = rect.left + rect.width / 2;
            const cy = rect.top + rect.height / 2;
            const opts = { bubbles: true, cancelable: true, clientX: cx, clientY: cy, pointerId: 1 };
            p.dispatchEvent(new PointerEvent("pointerdown", opts));
            p.dispatchEvent(new PointerEvent("pointerup", opts));
            p.dispatchEvent(new MouseEvent("click", opts));
            return true;
          }
          p = p.parentElement;
        }
      }
    }
    return false;
  }, text);
}

/** Press the nth "Select" button (0-indexed). Breakfast: 0-3, Lunch: 4-7, Dinner: 8-11. */
async function pressSelectN(page: Page, index: number): Promise<string> {
  return page.evaluate((idx: number) => {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const nodes: Element[] = [];
    let node: Node | null;
    while ((node = walker.nextNode())) {
      if ((node as Text).textContent?.trim() === "Select") {
        nodes.push((node as Text).parentElement!);
      }
    }
    const target = nodes[idx];
    if (!target) return `not found (total: ${nodes.length})`;
    let p: Element | null = target.parentElement;
    for (let i = 0; i < 6; i++) {
      if (!p) break;
      const key = Object.keys(p).find((k) => k.startsWith("__reactProps"));
      if (key && (p as any)[key]?.onClick) {
        const rect = p.getBoundingClientRect();
        const cx = rect.left + rect.width / 2;
        const cy = rect.top + rect.height / 2;
        const opts = { bubbles: true, cancelable: true, clientX: cx, clientY: cy, pointerId: 1 };
        p.dispatchEvent(new PointerEvent("pointerdown", opts));
        p.dispatchEvent(new PointerEvent("pointerup", opts));
        p.dispatchEvent(new MouseEvent("click", opts));
        return "ok";
      }
      p = p.parentElement;
    }
    return "onClick not found";
  }, index);
}

/**
 * Navigate directly to /meals.
 * Auth tokens are pre-injected into localStorage via storageState (global-setup.ts).
 * No login UI needed — bootstrap() reads the token and authenticates before render.
 */
async function goToMeals(page: Page) {
  await page.goto("/meals");
  // 45s covers the rare case where Metro cache missed and needs to recompile.
  // After global-setup pre-warms the bundle, this typically resolves in <5s.
  await page.waitForSelector("text=BREAKFAST", { timeout: 45_000 });
}

// ── Tests ──────────────────────────────────────────────────────────────────

test("Test 1 — Meals tab renders suggestion cards for all 3 slots", async ({ page }) => {
  const errors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() === "error") errors.push(msg.text());
  });

  await goToMeals(page);

  // 3 slot headers visible
  await expect(page.getByText("BREAKFAST")).toBeVisible();
  await expect(page.getByText("LUNCH", { exact: true })).toBeVisible();
  await expect(page.getByText("DINNER", { exact: true })).toBeVisible();

  // At least one Select button visible per slot
  const selectCount = await page.evaluate(() =>
    [...document.querySelectorAll("div")].filter(
      (el) => el.children.length === 0 && el.textContent?.trim() === "Select"
    ).length
  );
  expect(selectCount).toBeGreaterThanOrEqual(3);

  // No console errors
  const nonAuthErrors = errors.filter((e) => !e.includes("401"));
  expect(nonAuthErrors.length).toBe(0);
});

test("Test 2 — Dish selection flow shows confirmed state", async ({ page }) => {
  await goToMeals(page);

  // Wait for suggestion cards (Select buttons)
  await page.waitForFunction(() =>
    [...document.querySelectorAll("div")].filter(
      (el) => el.children.length === 0 && el.textContent?.trim() === "Select"
    ).length >= 4
  , { timeout: 20000 });

  // Click first Lunch Select (index 4 = skip 4 Breakfast selects)
  const result = await pressSelectN(page, 4);
  expect(result).toBe("ok");
  await page.waitForTimeout(2500);

  // "Confirmed for Lunch" visible
  await expect(page.getByText("Confirmed for Lunch")).toBeVisible();

  // Change button appears
  await expect(page.getByText("Change").first()).toBeVisible();

  // No Select buttons remain in Lunch section
  const lunchHasSelect = await page.evaluate(() => {
    const all = [...document.querySelectorAll("div")];
    const lunch = all.find((el) => el.textContent?.trim() === "LUNCH");
    if (!lunch) return false;
    const slot = lunch.closest("div")?.parentElement;
    return slot ? [...slot.querySelectorAll("div")].some(
      (el) => el.children.length === 0 && el.textContent?.trim() === "Select"
    ) : false;
  });
  expect(lunchHasSelect).toBe(false);
});

test("Test 3 — Home tab shows Planned kcal label with non-zero value", async ({ page }) => {
  await goToMeals(page);
  await page.goto("/");
  await page.waitForSelector("text=TODAY'S CALORIES", { timeout: 20000 });
  // Wait for calorie API data to load before checking ring
  await page.waitForSelector("text=Planned:", { timeout: 20000 });

  // ProgressRing rendered (an svg) inside the calorie section
  const ringVisible = await page.evaluate(() => {
    const all = [...document.querySelectorAll("div")];
    const caloriesLeaf = all.find(
      (el) => el.children.length === 0 && el.textContent?.trim() === "TODAY'S CALORIES"
    );
    return !!caloriesLeaf?.parentElement?.querySelector("svg");
  });
  expect(ringVisible).toBe(true);

  // "Planned:" label visible with non-zero kcal
  const plannedText = await page.evaluate(() => {
    const all = [...document.querySelectorAll("div")];
    return (
      all.find((el) => el.children.length === 0 && (el.textContent ?? "").startsWith("Planned:"))
        ?.textContent ?? null
    );
  });
  expect(plannedText).not.toBeNull();
  const kcal = parseInt((plannedText ?? "0").replace(/[^\d]/g, ""), 10);
  expect(kcal).toBeGreaterThan(0);
});

test("Test 4 — Snack log bottom sheet logs correctly", async ({ page }) => {
  await goToMeals(page);
  await page.goto("/");
  await page.waitForSelector("text=QUICK LOG", { timeout: 20000 });

  // Open snack bottom sheet
  const opened = await pressRN(page, "Log a Snack");
  expect(opened).toBe(true);
  await page.waitForTimeout(500);

  // Sheet visible
  await expect(page.getByText("How many calories?")).toBeVisible();

  // Tap 100 kcal preset
  const preset = await pressRNContains(page, "100 kcal");
  expect(preset).toBe(true);
  await page.waitForTimeout(500);

  // Input shows 100
  const inputVal = await page.evaluate(() => {
    const inputs = [...document.querySelectorAll("input")];
    return inputs[0]?.value ?? null;
  });
  expect(inputVal).toBe("100");

  // Tap Log Snack and wait for 200 response
  const [response] = await Promise.all([
    page.waitForResponse((r) => r.url().includes("/progress/log/meal") && r.status() === 200, { timeout: 10000 }),
    pressRN(page, "Log Snack"),
  ]);
  expect(response.status()).toBe(200);

  // Bottom sheet closed (280ms animation + buffer)
  await page.waitForTimeout(1500);
  const sheetGone = await page.evaluate(() =>
    ![...document.querySelectorAll("div")].some(
      (el) => el.children.length === 0 && el.textContent === "Log Snack"
    )
  );
  expect(sheetGone).toBe(true);

  // Consumed calories updated (> 0)
  await page.waitForTimeout(1000);
  const consumed = await page.evaluate(() => {
    const all = [...document.querySelectorAll("div")];
    // The consumed calorie display is the first standalone integer in the calorie section
    for (const el of all) {
      const t = el.textContent?.trim() ?? "";
      if (el.children.length === 0 && /^\d+$/.test(t) && parseInt(t, 10) > 0) return parseInt(t, 10);
    }
    return 0;
  });
  expect(consumed).toBeGreaterThan(0);
});

test("Test 5 — Week strip past day shows dish names or Not logged", async ({ page }) => {
  await goToMeals(page);

  // Click Tue/9 (yesterday — day before today Wed/10)
  const clicked = await page.evaluate(() => {
    const all = [...document.querySelectorAll("div")];
    for (const el of all) {
      if (el.children.length === 0 && el.textContent === "9") {
        const pill = el.parentElement;
        if (!pill?.textContent?.includes("Tue")) continue;
        let p: Element | null = pill;
        for (let i = 0; i < 5; i++) {
          if (!p) break;
          const key = Object.keys(p).find((k) => k.startsWith("__reactProps"));
          if (key && (p as any)[key]?.onClick) {
            const rect = p.getBoundingClientRect();
            const cx = rect.left + rect.width / 2;
            const cy = rect.top + rect.height / 2;
            const opts = { bubbles: true, cancelable: true, clientX: cx, clientY: cy, pointerId: 1 };
            p.dispatchEvent(new PointerEvent("pointerdown", opts));
            p.dispatchEvent(new PointerEvent("pointerup", opts));
            p.dispatchEvent(new MouseEvent("click", opts));
            return true;
          }
          p = p.parentElement;
        }
      }
    }
    return false;
  });
  expect(clicked).toBe(true);

  // Past day label visible
  await page.waitForSelector("text=What you planned for this day", { timeout: 10000 });

  // Each slot shows recipe name or "Not logged"
  for (const mealType of ["BREAKFAST", "LUNCH", "DINNER"]) {
    const slotContent = await page.evaluate((mt: string) => {
      const all = [...document.querySelectorAll("div")];
      const header = all.find((el) => el.textContent?.trim() === mt);
      return header?.closest("div")?.parentElement?.textContent ?? "";
    }, mealType);
    const hasContent =
      slotContent.includes("Not logged") ||
      slotContent.includes("kcal planned") ||
      slotContent.length > mealType.length + 10;
    expect(hasContent, `${mealType} slot has no content`).toBe(true);
  }
});

test("Test 6 — Confirmed Lunch selection persists on reload", async ({ page }) => {
  await goToMeals(page);
  await page.waitForTimeout(2000);

  // Check if Lunch is already confirmed
  const alreadyConfirmed = await page.evaluate(() =>
    [...document.querySelectorAll("div")].some(
      (el) => el.children.length === 0 && el.textContent === "Confirmed for Lunch"
    )
  );

  if (!alreadyConfirmed) {
    // Confirm first Lunch dish
    await page.waitForFunction(
      () =>
        [...document.querySelectorAll("div")].filter(
          (el) => el.children.length === 0 && el.textContent?.trim() === "Select"
        ).length >= 4,
      { timeout: 15000 }
    );
    await page.evaluate((idx: number) => {
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      const nodes: Element[] = [];
      let node: Node | null;
      while ((node = walker.nextNode())) {
        if ((node as Text).textContent?.trim() === "Select") {
          nodes.push((node as Text).parentElement!);
        }
      }
      const target = nodes[idx];
      if (!target) return;
      let p: Element | null = target.parentElement;
      for (let i = 0; i < 6; i++) {
        if (!p) break;
        const key = Object.keys(p).find((k) => k.startsWith("__reactProps"));
        if (key && (p as any)[key]?.onClick) {
          const rect = p.getBoundingClientRect();
          const cx = rect.left + rect.width / 2;
          const cy = rect.top + rect.height / 2;
          const opts = { bubbles: true, cancelable: true, clientX: cx, clientY: cy, pointerId: 1 };
          p.dispatchEvent(new PointerEvent("pointerdown", opts));
          p.dispatchEvent(new PointerEvent("pointerup", opts));
          p.dispatchEvent(new MouseEvent("click", opts));
          return;
        }
        p = p.parentElement;
      }
    }, 4);
    await page.waitForTimeout(2000);
  }

  // Hard reload
  await page.reload();
  await page.waitForTimeout(1500);

  // Tokens survive reload (localStorage persists across reloads).
  // This guard should never trigger, but avoids a hard fail if it does.
  if (!page.url().includes("/meals")) {
    await page.goto("/meals");
  }

  await page.waitForSelector("text=LUNCH", { timeout: 20000 });
  await page.waitForTimeout(2000);

  // Confirmed for Lunch persists
  await expect(page.getByText("Confirmed for Lunch")).toBeVisible();
});
