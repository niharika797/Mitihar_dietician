# Audit Session — 2026-07-29

Live audit while product owner explores the running apps. Notes appended as discovered.
Read-only intent on code; local stack booted for exploration. Target: **local backend + local Postgres**, both frontends local.

---

## 0. Environment recon

- `mityahar_postgres` container UP (5432). Backend was down at start.
- **No Redis container running** (only postgres up). `REDIS_URL` still set to `localhost:6379` in `.env`, so the lifespan `redis.ping()` will log an error but backend still starts; rate limiter degrades. Not blocking for audit — note it.
- node v24.18.0, pnpm 11.9.0, venv present.
- Frontend env files exist: `mitihar-frontend/apps/.env`, `mitihar-patient-app/.env` (not inspected — secret-scan blocked grep; left untouched).

---

## 1. Meal recommendation engine — code read (`app/services/meal_generator/meal_generator.py`)

**Shape of output:** 7 days × 3 meals (Breakfast/Lunch/Dinner). Each slot generates **4 combos** (PD-1). Weekly total = 84 combo rows (7×3×4). Snacks fully removed.

**Target math:**
- BMR → TDEE → macros via `calculations.py`. Split `{B:0.25, L:0.35, D:0.25}` = 0.85; remaining **15% is passive buffer**, applied once in `compute_meal_targets`. Doctor `PatientMealConfig.meal_split_override` (int %, sums to 85) overrides.
- Per-dish calorie scaling `factor = target_cal / cal_per_serving`, **clamped 0.5–3.0**. → a 200 kcal dish forced into a 700 kcal slot maxes at 3× = 600, undershoots. Clamp can silently miss the slot target. WATCH.

**Slot composition (in-code constants, NOT the meal_templates table):**
- Breakfast: main_dish 0.78 / accompaniment 0.22 (beverage removed, Session 22E).
- Lunch/Dinner: `template.slots`, with 40% chance of a one-pot variant (one_pot 0.70 / accompaniment 0.30) tried first, standard as fallback.
- `meal_templates` table (180 rows) is queried ONLY to fetch `template.slots` for L/D. Region/plan_type/diet filter with veg fallback. If no template → meal skipped entirely (logged). Potential silent gap if a (region, plan_type) pair has no template.

**Pool selection (`_pick_for_slot`) — 3 hard levels + Level 4:**
- Filters: `slot_type`, `diet_type`, `meal_time_tags`, **`is_verified=True`** (never serves unverified/test dishes), calorie band `target/3 .. target/0.5`, exclude daily/combo/weekly used, exclude blocked + avoided ids, exclude `avoid_tags`.
- Sort: prefer_tags/pinned/preferred (desc) → region → |cal−target|. `.limit(10)` then Python-side pick.
- Level 1 primary pool weekly-excluded → L2 weekly dropped → L3 diet fallback (Veg) → **L4: reuse combo-0's dish verbatim** rather than drop a required slot.
- **Allergy filter** `_is_allergenic`: substring match of allergen in ingredient name over `recipe_ingredients` (clinical-safety path). Substring = coarse (e.g. "nut" hits "butternut", "coconut"). WATCH — could over- or under-filter.
- **BLOCKLIST_PATTERNS** (chutney/powder/pickle/papad/…) skip only for PROTECTED_SLOTS (grain/dal/main/sabzi/one_pot) — stops a pickle landing as a main dish.

**Variety controls:** `daily_used_ids` (hard, cleared per day), `combo_slot_used_ids` (hard, per slot's 4 combos), `weekly_used_ids` (soft, dropped at L2). `used_food_ids` returned = only IDs picked THIS gen (not the seed) — prevents exclusion-set snowball across regenerations.

### Early code-level flags (to verify against real output)
1. **Factor clamp 0.5–3.0** can leave a slot well under target when the pool has no dish near the slot's kcal. → check real combos' `total_calories` vs `meal_target`.
2. **Allergy substring match** — false pos/neg risk on ingredient names. Clinical safety path; worth a real test (e.g. allergy "nut").
3. **avoid_pcos / avoid_gout tags match 0 food_items** (per generator-notes) — silent no-op filters. PCOS/Gout patients get no condition filtering today.
4. **No template → meal silently skipped** — a (region, plan_type) with no meal_templates row drops that meal with only a log line.
5. **Accompaniment pool thin** (known) → frequent Level-4 combo-0 duplication = 4 "combos" that are partly identical. → check how often combos repeat dishes.

---

## 2. Live app bring-up

| Service | Status | URL |
|---|---|---|
| Backend (uvicorn) | ✅ UP | http://localhost:8001 (`/health` ok) |
| Postgres | ✅ UP (container) | 5432 |
| Redis | ✅ UP (started `mityahar-redis` container) | 6379 |
| Doctor dashboard (Vite) | ✅ UP | http://localhost:5173/ |
| Patient app (Expo web) | ❌ **FAILED to bundle** | — |

- Backend redis warning at first boot (Redis was down); started container after — slowapi RedisStorage reconnects per-request, no backend restart needed.
- CORS verified: backend allows `localhost:5173`, `8081`, `3000` (preflight echoes origin). No CORS blocker.
- Frontends launched with API base forced to `http://localhost:8001/api/v1` via shell env (`VITE_API_URL` / `EXPO_PUBLIC_API_URL`) — **`.env` files NOT modified** (permission-blocked anyway).

### 🔴 Patient web app broken
```
Metro error: (0 , _reactNavigationNative.createScreenFactory) is not a function
```
- React Navigation ↔ Expo Router version mismatch; web bundle falls back to `_error.js`. Patient app cannot be explored on web in current state. Native (`pnpm android`) untested. Needs a dep-version fix before web exploration is possible.

---

## 3. Recommendation quality — live data (rec 409, patient 51: F/31, LA, TDEE 1761, Veg, goal=weight_loss)

**Structure verified:** `weekly_combos` table (NOT `recommendations.meals`, which is empty `[]` on all 127 rows) holds 84 combos = 21 slots (7×3) × 4 combos. Clean.

**Calorie targets:** every combo's `total_calories` is EXACT and identical — B=440, L=616, D=440 (0.25/0.35/0.25 × 1761). Dishes are rescaled (`factor` 0.5–3.0) to hit target, so **the displayed calorie always equals the target and never reflects the real dish** — by design, but means calorie is not an informative signal. Factor clamp never bound for this patient (no deviation from 440/616).

**Variety (good where pool is deep):**
- Level-4 combo-0 duplication: **0 of 63** non-zero combos — main/one_pot pools deep enough. Good.
- Distinct dishes/week: Lunch 34, Dinner 31 — healthy. Breakfast only **13 distinct** across the week — thin.

**🔴 Accompaniment slot is the weak point:**
- In ONE week's plan: Masala Chaas **26×**, Meethi Lassi 14×, Plain Dahi 12×. Patient sees the same drink/curd with nearly every lunch & dinner.
- Accompaniment slot is being filled by **beverages/curd** (Chaas, Lassi, Dahi, Sambar). Product spec says beverages are a *separate category "not tied to meal slots."* Either the `slot_type='accompaniment'` pool is dominated by beverage-like items, or beverages are mis-serving into accompaniment. **Product-owner question.**

### 🔴 Weight-loss patients get maintenance calories (no deficit)
- `calculate_macronutrients` only changes macro **ratios**, never reduces TDEE. Deficit logic exists nowhere in the target path.
- The `weight_loss` branch fires ONLY when `health_condition == 'Gym-Friendly'`. A patient whose `health_condition='Healthy'` but `health_goals=['weight_loss']` (exactly patient 51) gets **no macro change and no calorie cut** — meal targets = full TDEE (1761). The 15% buffer is passive snacking, explicitly NOT a deficit.
- Net: the weight-loss goal does not translate into any calorie reduction unless a doctor manually lowers the split. **Verify intended behaviour with product owner** — likely a gap between onboarding "goal" and the calorie engine.

### ✅ Correction to stale notes
- `.claude/rules/generator-notes.md` claims `avoid_pcos`/`avoid_gout` match 0 food_items. **Stale.** Live: `avoid_pcos`=554, `avoid_gout`=130 tagged. PCOS/Gout condition filtering works today. (Full avoid-tag coverage: ibs 892, pcos 554, gluten 278, diabetes 155, gout 130, fattyliver 121, highchol 45, kidney 44, heart 38, hyperthyroid 28, hypothyroid 23, **hypertension only 6** — hypertension avoid-filter is near-useless.)
- Prefer-tags: gluten_free 1836, calcium_rich 368, iron_rich 255, diabetes_friendly 146, … pcos_friendly 53.

### Other flags (from code, not yet reproduced live)
- Allergy filter = substring match of allergen in ingredient name (`_is_allergenic`) → "nut" matches coconut/butternut. Clinical-safety path; coarse. Test before trusting.
- `hypertension` avoid pool = 6 items → effectively no filtering for hypertensive patients.
- No meal_template for a (region, plan_type) pair → meal silently skipped (log only).

---

## 4. Nutrition provenance (traced from live DB + scripts)

Full chain, root → dish:
```
6k recipe dataset (external, scraped) ─seed_6k_recipes.py→ food_items.ingredients JSONB (amount_g)
   ─seed_recipe_ingredients.py→ recipe_ingredients.quantity_g   ← qty_g origin; NEVER validated/recomputed
   × ingredients.*_per_100g  ─recalculate_recipe_nutrition.py→ food_items.cal_per_serving
food_items.serving_weight_g = independent field from the 6k import (NOT the ingredient sum → mismatches, e.g. 305)
```
- **`qty_g` = the scraped dataset's own amounts.** Root cause of the 8000g-makhana garbage. 564 rows >300g, 25 >1000g, max 2000g remain.
- **Ingredient nutrition is NOT mostly IFCT.** source: estimated_llm 754 (79%), pending/empty 93 (10%), **IFCT2017 88 (9%)**, LLM 15. The "ICMR foundation" is mostly LLM guesses today.
- **IFCT importer only read Table 1 (proximates).** Minerals (Na/Fe/Ca — Tables 2+) were never imported → those columns empty → nutrition-driven hypertension/anemia/osteoporosis filtering impossible. Coverage also name-match-limited (88/950).
- Duplicates: 292 names have >1 food_items row → ~350 extras (e.g. "Masala Chaas" = 4 rows). Cause = bulk import, NOT calorie divergence (dedup keys on name, never kcal). Fix order: repair quantities → then dedup by name.
- Unused source data sitting in `data/`: `INDB.zip` (the intended master per BUILD_TRACKER), `USDA_SR.zip`.

## 5. IFCT2017 full-PDF extraction (in progress — new work this session)

Goal: extract all 12 IFCT tables + food-code table + ingredient images to xlsx/json, exact values.
- **Engine:** `scripts/extract_ifct_tables.py` — PyMuPDF word geometry, **no OCR** (text layer only → no number hallucination), fully local. camelot rejected (honors the PDF's no-extraction permission flag); pdfplumber text mangles values on long rows; fitz `find_tables` drops rows. Final method = code-anchored y-bands → x-position column mapping, with value-count branching for multi-layout tables.
- **Table 1 (pp 41-68): DONE — 528 rows, 3,872 values, full-file verify vs raw text = 0 mismatches.** Handles the two physical layouts (plant 9-col; animal meat/fish 5-col: no fibre/carb) + 8 oddball juice/beverage rows (x-band fallback, verified). Below-detectable-limit blanks preserved (never coerced to 0). Values kept verbatim as `mean±SD`.
- Output: `data/IFCT2017_extracted/IFCT_Table{n}.xlsx` + `.json` + combined `IFCT2017_all_tables.xlsx`.

### Progress (certified = every value present in source text layer, exact)
| Table | Pages | Rows | Status |
|---|---|---|---|
| 1 Proximates | 41-68 | 528 | ✅ certified, 0 loss |
| 2 Water-sol vitamins | 71-98 | 528 | ✅ certified, 0 loss |
| 3 Fat-sol vitamins | 101-128 | 528 | ⚠ values exact, **11 collision cells dropped** (0.4%) — sparse 11-col, needs anchor tweak |
| 4 Carotenoids | 131-147 | 329 | ✅ certified; row count 329 not 528 (carotenoids likely plant-only — confirm) |
| 5 Minerals & Trace | 151-206 | 528 | ✅ certified, 0 loss, 8104 values — **double-wide handler built.** Na/Fe/Ca/K/P/Zn all correct (wheat A019: CA 30.94, FE 4.10, NA 2.04, K 311, P 315) |

- **`wide2` layout handler done** (double-page-wide merge by food code) — generalizes to Tables 7, 8, 10. Table 5 columns: left `AL AS CD CA CR CO CU FE PB LI`, right `MG MN HG MO NI P K SE NA ZN` (20 total).
- **Note on names:** wide-table left-page names can come out slightly reordered (e.g. A001 "Amaranth cruentus) seed, black"). Food CODE is authoritative — best practice is to take clean Food Names for ALL tables by joining on code to Table 1 (or the food-code table pp 552-584), not from each table's own name column.
- **Table 5 is the medical-filtering unlock** — feeding NA→hypertension, FE→anemia, CA→osteoporosis rank/filter directly from data instead of the sparse tags.

### FINAL extraction state (session end — stopped at Table 7 per product-owner call; images dropped)
| Table | Rows | Values | Status |
|---|---|---|---|
| 1 Proximates | 528 | 3872 | ✅ 0 mismatch |
| 2 Water-sol vitamins | 528 | 3725 | ✅ 0 mismatch |
| 3 Fat-sol vitamins | 528 | 2857 | ✅ 0 mismatch (11 collision cells to clean) |
| 4 Carotenoids | 329 | 1278 | ✅ 0 mismatch |
| 5 Minerals & Trace | 528 | 8104 | ✅ 0 mismatch — Na/Fe/Ca/K/P/Zn |
| 6 Starch & Sugars | 314 | 1754 | ✅ 0 mismatch — diabetes/PCOS (validated: CHO=STARCH+free-sugars) |
| 7 Fatty Acid Profile | 507 | 5245 | ✅ 0 mismatch — FASAT/FAMS/FAPU for heart/cholesterol |

- **Reality-check decision:** Tables 1-5 cover 100% of what the current platform consumes; Table 6 (sugars) + 7 (fatty acids) added for future diabetes-sugar and heart-satfat filters. Tables 8-12 (amino acids, organic acids, polyphenols, phytosterols, oil fats) NOT needed — Mityahar's model doesn't use them. Images (pp 478-549) dropped.
- Row counts <528 (T4 329, T6 314, T7 507) = those nutrients only measured for a subset of foods (mostly plant/edible-portion), not extraction loss — every food present verifies exact.
- **All output:** `data/IFCT2017_extracted/IFCT2017_all_tables.xlsx` (7 sheets) + per-table `.json`. Decrypted copy `IFCT2017_dec.pdf` (camelot-ready).
- Script: `scripts/extract_ifct_tables.py` — PyMuPDF word-geometry, no OCR, local. Handles single-wide + `dual` (plant/animal) + `wide2` (double-page) layouts; verifier = fitz full-page text.

### NEXT (highest leverage — not the remaining PDF tables)
Wire Table 5 minerals into the `ingredients` table: match 528 IFCT foods → ingredient rows, populate the empty `sodium/iron/calcium_per_100g` columns, then switch the medical filter from the sparse 6-dish `avoid_hypertension` tag to **computed sodium** (and Fe→anemia, Ca→osteoporosis). Use IFCT food CODE as the join key; take clean Food Names from Table 1 (wide-table names can be reordered).

### Structural findings that shape remaining work
- **Verifier was the bug, not the extractor.** pdfplumber (old baseline) wraps long-name rows and drops values → false mismatches. Switched to **fitz full-page text** baseline (complete). All 4 tables verify 0-mismatch under it.
- **Decrypted a working copy** (`pikepdf` → `IFCT2017_extracted/IFCT2017_dec.pdf`) — strips the PDF's no-extraction permission flag so **camelot** runs as an independent cross-check (clean headers confirmed). Available for column-order verification on the hard tables.
- 🔴 **Table 5 (minerals — Na/Fe/Ca, the medical-filtering unlock) is DOUBLE-PAGE-WIDE:** each food spans two facing pages (left-half cols | right-half cols), so pp 151-206 yield 1056 half-rows for 528 foods. Needs a merge-by-food-code handler. The long ranges Table 7 (227-293), Table 8 (297-361), Table 10 (384-451) are almost certainly double-wide too.

### Remaining work (realistic — multi-session)
1. Double-page-wide merge handler → Tables 5, 7, 8, 10 (stitch each food's two page-halves by code).
2. Per-table schemas + extraction for Tables 6, 9, 11, 12 (single-wide).
3. T3: fix the 11 collision cells.
4. Column-ORDER cross-check (via camelot on the decrypted copy) for the sparse vitamin/mineral tables — current column order is trusted from header sequence, not independently verified.
5. Food-code/name table (pp 552-584).
6. Ingredient images (pp 478-549) → PyMuPDF, one file per food code.
- Engine + verifier are proven; each remaining table is a bounded fix, not a rewrite.

