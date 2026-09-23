# Dish Duplicate Audit — Stage 6, Section 0

**Date:** 2026-07-15 · **DB:** local dev (`mityahar_db`, post Stage 2/3) · **Read-only** — no data was modified.

## Method

- Grouped all 2,137 `food_items` rows by normalized `recipe_name`: lowercase, trimmed, internal whitespace collapsed (`re.sub(r'\s+', ' ', name.strip().lower())`). This closes the gap in Stage 2's `norm()` (`scripts/backfill_recipe_ingredients.py:47-48`, strip+lower only) — though in practice the gap is cosmetic: whitespace collapse produced **0 additional duplicate groups** on current data.
- **Tier 1 (exact duplicate):** within a group, all seven macro fields equal (`cal/protein/carbs/fat/fiber/sodium_per_serving`, `serving_weight_g`) **and** the `recipe_ingredients` sets equal as `(ingredient_id, quantity_g)` pairs. The deprecated `ingredients` JSONB was not used (retired from read paths in Stage 2).
- **Tier 2 (conflict):** same normalized name, any macro or ingredient difference.

## Headline counts

| Metric | Count |
|---|---|
| Total `food_items` rows | 2,137 |
| Distinct normalized names | 1,769 |
| Duplicate groups (>1 row per name) | **295** (663 rows) |
| **Tier 1 — exact duplicates** | **144 groups**, 305 rows → **161 rows removable** |
| **Tier 2 — conflicting** | **151 groups**, 358 rows |

### Prior 284 figure — confirmed

The earlier report's number (284 same-name+same-slot groups in the verified pool) **holds exactly**: verified pool (`is_verified=True`), grouped by normalized name + `slot_type` → **284 groups / 612 rows** on current post-Stage-2/3 data.

## Tier 1 detail (144 groups)

- Sizes: 139 groups of 2, 2 groups of 3, 3 groups of 7.
- Verified status: 140 groups all-verified, 4 all-unverified, 0 mixed — so "pick the Verified row as canonical" never has to arbitrate a mixed group; canonical choice within all-verified pairs is arbitrary (rows are identical).
- 0 groups are "identical because both have zero ingredients" — every Tier 1 group matches on real ingredient data.
- **3 groups match on macros+ingredients but differ on `diet_type`** (one also on `slot_type`): `morning chai coffee` (229 Veg / 239 Non-Veg), `salad dressing` (231 Veg / 237 Non-Veg), `dahi bowl` (240 accompaniment-Veg / 310 dal_protein-Veg / 318 accompaniment-NonVeg). These look like deliberate diet-variant clones so both diet pools contain the dish. **Excluded from Tier 1 auto-merge** — merging would remove the dish from one diet pool.
- **3 of the 144 groups are test artifacts**, not real dishes: `doctor2 private dal` (7 rows, ids 3697–3715), `global test recipe` (7 rows, 3698–3716), `to be rejected recipe` (7 rows, 3699–3717, source=`rejected`). Consecutive ids from repeated `full_backend_test.py` runs. Candidates for deletion/flagging rather than merge — needs sign-off.
- Net **real** Tier 1 scope after exclusions: **138 groups, ~140 rows removable** (mostly 6k_dataset pairs, e.g. `rabodi ki sabzi` ×3).
- Sources: 138 groups pure 6k_dataset, 3 excel, 3 test-artifact sources.

## Tier 2 detail (151 groups)

- Sizes: 105×2, 39×3, 5×4, 1×5, 1×6.
- Verified status: 148 all-verified, 3 mixed — nearly the whole conflict set is live in the generator pool right now, serving whichever row the picker lands on.
- Conflict shape: **149 of 151 differ in both macros and ingredients**; 2 differ in ingredients only (identical macros); 0 differ in macros only. So almost nothing here is a pure stale-recompute case at the ingredient level — but 55/151 groups have the *same ingredient count* per row, suggesting same recipe with different quantities/ingredient-ids (recompute + source check territory).
- 15 groups also differ on `slot_type`; 1 group has a row with zero `recipe_ingredients`.
- Sources: 123 groups internal 6k_dataset conflicts, 19 excel-vs-6k_dataset, 8 excel-internal, 1 three-way.
- Magnitude examples (excel vs 6k rows disagree wildly): `dhokla` 281 vs 790 kcal, `medu vada` 206 vs 671 kcal, `raab` 147 vs 502 kcal — consistent with the known 6k_dataset whole-recipe-vs-per-serving scaling issue found in Stage 2.

## RBAC finding (scoping question 2)

Roles are **three separate tables**, not one user table with a role column: `Doctor` (`app/models/db_models.py:117`), `Admin` (`:132-148`, own `allowed_ips` JSONB at `:141`), `Patient` (`:192`). Each issues a JWT with a `role` claim (`app/routers/auth.py:49,60,69`); enforcement is:

- `get_current_admin` dependency — `app/core/security.py:205-214` (decode JWT → `role=="admin"` → `is_active`), already used on every route in `app/routers/admin.py`.
- `AdminIPWhitelistMiddleware` — `app/core/middleware.py:223-288`, fires only on `/api/v1/admin/*`, checks IP against `Admin.allowed_ips`, **fails open** on DB error (`:285-288`).
- `DoctorIsolationMiddleware` — `app/core/middleware.py:116-139`, `role=="doctor"` gate on `/doctor/*`.

**Conclusion: no new role is needed.** The `admin` tier already exists as a distinct auth path (separate table + JWT role + dependency + IP whitelist). The Stage 6 admin review UI can gate on `Depends(get_current_admin)` and live under `/api/v1/admin/*` (inheriting the IP whitelist). "Promote a doctor later" = insert a row in `admins` — no schema change now. Single admin account already exists via `scripts/seed_admin.py`.

## Open items needing sign-off before build

1. **Test artifacts (21 rows, ids 3697–3717):** delete outright, or soft-flag? They should not go through Tier 1 merge.
2. **Diet-variant "duplicates" (3 groups):** confirm exclusion from Tier 1 (recommended), or define a merge rule that preserves both diet pools.
3. **Soft-delete mechanism:** `food_items` has **no** `is_deleted`/`deleted_at` column today — the current soft-flag convention is `is_verified=False` (removes from generator pool but keeps the row browsable). Tier 1 merge spec says "soft-delete the duplicate": reuse `is_verified=False` + audit-log, or add a real `deleted_at` column? Latter recommended (unverified ≠ deleted; the Data Review tab would otherwise show merged corpses as reviewable dishes).
4. Tier 2's dominant pattern is the **6k_dataset scaling problem**, not subtle nutrition disagreements — the AI research step's "recompute bottom-up first" order is the right call and will likely resolve the bulk mechanically.
