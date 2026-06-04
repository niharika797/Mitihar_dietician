# Mityahar — Build Tracker
**Last updated:** Session 16 (2026-06-04)  
**Next session:** Session 17  
**Maintained by:** Claude Code — read at session start, update at session end.

---

## HOW TO USE THIS FILE

1. **Every session starts here.** Read this file completely before touching any code.
2. **Every session ends here.** Update STATUS, add findings, mark completed items, note blockers.
3. **Never guess at prior decisions.** If something seems wrong or contradicts this file, ping the product owner before proceeding.
4. **Cross-reference:** Full audit reports are in `docs/` — this file is the index, not the full record.

---

## PLATFORM OVERVIEW

**Three services:**
- Backend: FastAPI → `localhost:8001` (project root)
- Doctor Dashboard: React + Vite → `localhost:5173` (`mitihar-frontend/apps/`)
- Patient App: Expo Web → `localhost:8081` (`mitihar-patient-app/`)

**Project root:** `C:\Users\Lenovo\Desktop\Code\2026\Nutria\Mitihar_dietician`  
**DB:** `postgresql+asyncpg://admin:mityahar_dev@localhost:5432/mityahar_db`

**Credentials:**
| Role | Email | Password |
|------|-------|----------|
| Doctor | dr.ashok.mehta@mitihar.test | DoctorTest@2026 |
| Admin | admin@mitihar.test | Admin@2026 |
| Test patient (subscribed) | testaudit@mityahar.com | Test@1234 |
| Test patient (subscribed) | priya.test@mityahar.com | Test@1234 |

**Subscription codes:** ASHOK1 (consumed), ASHOK2 (consumed by Priya), ASHOK3–ASHOK5 (available)

---

## PRODUCT DECISIONS — LOCKED

These are confirmed decisions from the product owner. Do not change direction on any of these without explicit product owner confirmation.

### Meal Structure
- 3 meals only: Breakfast, Lunch, Dinner — MorningSnacks and EveningSnacks removed entirely
- Default TDEE split: Breakfast 25% / Lunch 35% / Dinner 25% / Buffer 15%
- Buffer is passive — absorbs casual snacking, not tracked unless patient logs it
- Doctor can override the split per patient (e.g. 10/45/30 for a breakfast-skipper)
- Buffer % stays constant at 15% regardless of split adjustments

### Ingredient & Recipe Display
- Macro-only display on patient app and doctor dashboard — no gram quantities shown
- Proportional labels for ingredients: "large portion / small bowl / 1 tsp / pinch"
- Shopping list: ingredient names only, no quantities
- Beverages: separate manageable category, not tied to meal slots, expandable database

### Adaptive Meal Suggestions (planned, not yet built)
- Patient sees 3–4 dish options per meal slot, picks one
- Daily calorie budget depletes as patient logs choices
- Next meal suggestions sized to remaining budget
- Doctor sets pool parameters (prefer / avoid / pin / block per dish)
- Doctor sees weekly summary of what patient actually chose

### Doctor Controls
- Doctor adjusts TDEE split per patient from dashboard
- Doctor pins preferred dishes or blocks specific dishes per patient
- Doctor reviews AI-generated condition tags and corrects if wrong — corrections update master database
- Doctor adds recipes through dashboard (with proper fields)
- Doctor weekly summary: what patient chose, calorie trends, adherence

### Medical Condition Filtering
- Two-tag model per condition: avoid tag + prefer tag
- Filters activate automatically from onboarding — no doctor confirmation step needed
- Doctor can override/refine after the fact

**Full condition tag schema:**
| Condition | Avoid Tag | Prefer Tag |
|-----------|-----------|------------|
| Type 2 Diabetes / Pre-diabetes | `avoid_diabetes` | `diabetes_friendly` |
| Hypertension | `avoid_hypertension` | `heart_friendly` |
| Hypothyroidism | `avoid_hypothyroid` | `thyroid_support` |
| Hyperthyroidism | `avoid_hyperthyroid` | — |
| PCOS/PCOD | `avoid_pcos` | `pcos_friendly` |
| High Cholesterol | `avoid_highchol` | `cholesterol_friendly` |
| Kidney Disease | `avoid_kidney` | — |
| Celiac Disease | `avoid_gluten` | `gluten_free` |
| IBS/IBD | `avoid_ibs` | `gut_friendly` |
| Fatty Liver | `avoid_fattyliver` | `liver_friendly` |
| Gout | `avoid_gout` | — |
| Osteoporosis | — | `calcium_rich` |
| Anemia | — | `iron_rich` |
| Heart Disease | `avoid_heart` | `heart_friendly` |

### Health Goal vs Medical Condition (two separate layers)
- Goals (Weight Loss, Muscle Gain, etc.) → drive calorie and macro targets
- Medical conditions → drive dish pool filtering via tags
- Both layers applied simultaneously and silently
- Onboarding keeps them as two separate steps for the user

### Ingredient Nutrition Source
- Master ingredients table sourced from INDB (open-source, ICMR-verified) as foundation
- Fitterfly API considered for Phase 2 when scaling
- Architecture: ingredients table → recipe_ingredients → food_items (calculated nutrition)
- Nutrition is never manually typed — always calculated from ingredient level up

### Database Transition
- Soft transition (Option B): unverified recipes remain active, verified recipes prioritized
- Verified vs unverified flag visible to doctors on dashboard
- Doctors and developers both have access to correct and edit ingredient data

### Subscription & Onboarding
- Three-state code lifecycle: AVAILABLE → RESERVED (at registration) → CONSUMED (at activation)
- token_1 generated at activation only (not at onboarding)
- token_1 unique per patient, expires 30 days from activation
- Onboarding store persists to device storage — survives app kill mid-flow
- Free users see teaser meal plan (3 meals, gradient lock, Find a Doctor CTA)
- Seamless unlock when code activated — no refresh needed

### Freemium
- No in-app payment — patient contacts doctor offline, gets code, enters it
- Free users: teaser meal plan (same for all, partially locked)
- Subscribed users: full personalized meal plan
- Find a Doctor accessible to all users regardless of subscription

---

## TARGET ARCHITECTURE

```
ingredients table (master, ICMR-verified)
         ↓
recipe_ingredients table (recipe + ingredient + quantity in grams)
         ↓
food_items table (recipe metadata + calculated nutrition)
         ↓
meal_slot dishes[] (individual food_items with food_id, slot_type, per-dish macros)
         ↓
recommendations table (meal slots grouped by date, combined for display)
```

**Key principle:** Nutrition flows upward from verified ingredient data. Never manually typed at recipe or meal level.

---

## WHAT IS FULLY WORKING ✅

All of the following have been built and verified across Sessions 1–8:

**Authentication & Subscriptions**
- Registration (with and without doctor code)
- Three-state subscription code lifecycle (AVAILABLE → RESERVED → CONSUMED)
- token_1 generation at activation with 30-day expiry
- token_2 (PatientVisit) created at activation
- Login race condition fixed
- Onboarding store persistence (survives app kill)
- Teaser meal plan for free users with gradient lock overlay
- Find a Doctor unblocked for free users
- Seamless subscription unlock

**Patient App**
- All 8 onboarding steps — data persisting correctly
- Home tab — all 5 meal slots (will reduce to 3), calorie ring, streak, quick log
- Meal logging — POST 200, UI updates
- Water, steps logging
- Progress tab — re-fetches on navigation, streak correct
- Week view — all meal types render
- Shopping list — ingredient names show (quantities still inflated — known issue)
- Meal detail — ingredients from Ingredients Scaling display

**Doctor Dashboard**
- Loads clean, no console errors
- Patient list with token_1 status, expiry, 30-day countdown
- Patient detail — all tabs (Overview, Plan, Activity, Notes, Visits)
- Recipe assignment works end to end
- Pending renewals endpoint returns 200

**Database**
- 326 recipes deduplicated (Milk ×10 in Chai fixed)
- SQLAlchemy ambiguous FK fix (registration no longer 500s)
- Expo web Zustand ESM fix (blank screen resolved)
- 6 recipes with 40,000g ingredient amounts fixed (150g each); "Gm " prefix names corrected
- 18 beverages misclassified as grain/sabzi/main_dish/snack_item moved to slot_type='beverage'; verified by template analysis that beverages cannot appear in Lunch/Dinner slots
- `is_verified` badge visible on recipe cards (Verified=green, Unverified=grey)
- `serving_weight_g` and `sodium_per_serving` fields added to doctor recipe creation form and backend schema

---

## KNOWN ISSUES — NOT YET FIXED ⚠️

| Issue | Severity | Blocked By |
|-------|----------|------------|
| Ingredient gram quantities unrealistic (batch data entry) | P1 | Architecture sessions 14–15 |
| Medical condition filtering does nothing | P1 | Session 18 |
| testaudit@mityahar.com token_1 shows Inactive (legacy account) | Low | Data artifact, not a bug |
| plan_type_tags identical on all 2,141 recipes (useless) | P1 | Session 18 |
| Shopping list shows names but no quantities are meaningful | P1 | Sessions 13–14 |
| 3 food_items still have "Gm " prefix ingredient names (Gm arhar dal ×1, Gm makhana ×2) — correct amounts, corrupted names only | P2 | Session 14 |
| 560g curry leaves in ID 2924 (Arabic Vegetable) — single-serving amount suspicious but not > 10,000g | P2 | Session 14 |
| ID 2674 (Drumstick Buttermilk Curry) slot_type='grain' — should be 'sabzi' (unrelated to beverage fix) | P2 | Session 14 |
| food_items IDs 3697–3715 recipe_name "Doctor2 Private Dal" — manual test data artifacts, not a bug | Low | Manual DB cleanup needed |
| TS error: MealEntry has no 'id' field — PlanTab.tsx line 888 uses meal.id which doesn't exist in the interface. Pre-existing before Session 16. | Low | Session 17 |
| TS error: Recipes.tsx AddRecipeForm missing submit_to_global field in addRecipe call. Pre-existing. | Low | Session 17 |
| recommendation_id backfilled on new dish ops — existing meal slots still null until next PATCH operation or plan regeneration | Low | Resolves gradually via use |

---

## SESSION BUILD PLAN

### SESSION 9 — P0 Database Fixes + Recipe Form Improvements
**Type:** Foundation (no /goal)  
**Status:** COMPLETE (2026-06-01)  
**Goal:** Fix actively wrong data before any architecture work begins.

Tasks:
- [x] Fix 6 recipes with ingredient amounts > 10,000g (industrial-scale corruption) — also cleaned "Gm " prefix from ingredient names in same transaction; 3 more with "Gm " names but valid amounts logged to KNOWN ISSUES for Session 14
- [x] Fix 18 beverage items with wrong slot_type — task said "8 items" but full audit found 18 clear beverages misclassified; 7 false positives (regex matched "Steamed" for "tea", "Chainsoo" for "chai") and 7 ambiguous milk-as-ingredient dishes correctly left untouched
- [x] `is_verified` flag already existed (added in prior session); 197 recipes pre-verified (184 excel-sourced, 13 doctor-submitted) — correct state, no migration needed
- [x] Verified flag now shows on recipe cards in doctor dashboard — green "Verified" badge, grey "Unverified" badge (replaced ambiguous amber "Pending" label)
- [x] Added `serving_weight_g` (required) and `sodium_per_serving` (optional) to doctor recipe creation form, `RecipeCreateRequest` schema, `FoodItem` constructor, `FoodItemSummary` response, and `RecipeCreateBody` TypeScript interface
- [x] All regression checks pass: meal logging 200, doctor recipes endpoint returns new fields, recipe creation stores both new fields correctly

**Session findings:**
- `is_verified` was already present with 197 verified recipes — task assumption was wrong, no work needed
- Beverage misclassification was broader than expected (18 not 8) due to keyword matching false positives
- Priya's stored plan has 3 legacy beverage-in-Lunch entries (pre-fix data) — will be cleaned when plan is regenerated in Session 12
- `amount_g` in task spec = `serving_weight_g` in DB schema — different names for the same concept

---

### SESSION 10 — Schema Design (Approval Required)
**Type:** Foundation (no /goal — needs product owner approval before migration)  
**Status:** COMPLETE (2026-06-01)  
**Goal:** Design the new data architecture. No migration yet — just schema definitions and product owner sign-off.

Tasks:
- [x] Design `ingredients` table schema — per-100g nutrition, INDB-compatible, glycemic_index excluded (removed per product owner review)
- [x] Design `recipe_ingredients` table schema — FK to food_items (CASCADE) and ingredients (RESTRICT), quantity_g CHECK > 0
- [x] Design `dishes[]` array structure for recommendations.meals JSONB — food_id, recipe_name, slot_type, per-dish macros
- [x] Design `beverages` table — standalone catalog, not tied to meal slots, 3 category types
- [x] Design `patient_meal_config` table — JSONB meal_split_override, one row per patient (lazy creation), separate from patients table
- [x] Design `patient_dish_preferences` table — doctor pin/block per patient-dish pair, preference_type CHECK IN ('pin','block')
- [x] Write schema as Alembic migration (revision c2d3e4f5a6b7) with full downgrade path
- [x] Product owner approved with 3 changes: glycemic_index column removed, CHECK constraints added to recipe_ingredients and patient_dish_preferences

**Session findings:**
- glycemic_index is a food/dish property, not an ingredient property — removed from ingredients table
- meal_split_override stored as single JSONB not separate Float columns — lazy table preferred over adding columns to patients
- PatientMealConfig and PatientDishPreferences ORM models do not exist in db_models.py at session end (added in Session 11)

---

### SESSION 11 — Generator Rewrite
**Type:** Foundation (no /goal)  
**Status:** COMPLETE (2026-06-01)  
**Dependencies:** Session 10 schema approved  
**Goal:** Rewrite meal_generator.py to produce correct structure and remove snacks.

Tasks:
- [x] Run Alembic migration c2d3e4f5a6b7 with 3 product-owner-approved changes — all 5 tables confirmed EXISTS
- [x] Add PatientMealConfig ORM model to db_models.py matching migration schema
- [x] Remove MorningSnacks and EveningSnacks from generation pipeline — meal_types, meal_time_mapping, meal_history dicts, all target calculation methods
- [x] Apply 0.85 multiplier to TDEE before distributing — `effective_tdee = targets["tdee"] * 0.85`
- [x] Check for patient-level meal_split_override before using DEFAULT_SPLIT (25/35/25) — PatientMealConfig ORM query in generate_meal_plan
- [x] Store dishes[] array per meal slot with food_id, recipe_name, slot_type, per-dish macros (calories/protein/carbs/fat/fiber)
- [x] Keep Menu Names as " + " joined string for backward compat display
- [x] Write food_id into each dish entry — food_id is FoodItem.id PK, accessible at line 407 and now written to dishes[]
- [x] meal_templates queries: no change needed — removing snacks from meal_types auto-excludes snack templates
- [x] Fix diet_plans.py validator: hardcoded 35 → EXPECTED_MEAL_COUNT = 7 × 3 = 21

**Session findings:**
- `user_data["id"]` is passed as string from the API route — `int(patient_id)` cast required before PatientMealConfig query (asyncpg does not implicit-cast varchar to integer column)
- `_validate_generated_plan` in diet_plans.py hardcoded 35 meals — updated to EXPECTED_MEAL_COUNT constant; this file was not in scope but the fix was a direct consequence of Task 4A
- `_calculate_meal_targets()` and all macro target methods (protein/carb/fiber/fat) are now dead code — replaced by effective_tdee + patient_meal_config logic in generate_meal_plan; left in place pending Session 12 cleanup
- All 4 verification checks PASS: 21 slots, no snacks, dishes[] present, food_id in every dish
- All regression checks PASS: meal plan 200, meal log POST 200, progress today 200

---

### SESSION 12 — Verification + Teaser Update + Dead Code Cleanup
**Type:** Verification + Cleanup  
**Status:** COMPLETE (2026-06-02)  
**Dependencies:** Session 11 complete ✅  
**Goal:** Confirm new generator output is correct, update teaser, clean dead code.

Tasks:
- [x] Verify Priya's plan: 21 slots confirmed (7×Breakfast + 7×Lunch + 7×Dinner), 0 snack slots, dishes[] present in all 21 meals, food_id present in every dish
- [x] Verify calorie math: TDEE×0.85 distributed 25/35/25 — plan structure correct; individual calorie values verified at slot level
- [x] Update teaser meal plan in meals.tsx to 3 meals only (removed MorningSnacks and EveningSnacks from TEASER_MEALS)
- [x] Update MEAL_ORDER in index.tsx, meals.tsx, week-view.tsx — removed MorningSnacks and EveningSnacks
- [x] Update MEAL_META in index.tsx — removed snack emoji/time entries
- [x] Update MEAL_HOUR in meal-detail.tsx — removed snack hour entries
- [x] Update MEAL_TYPES in log-meal.tsx — removed snack types
- [x] Remove dead code from meal_generator.py: `_calculate_meal_targets()`, `_calculate_protein_targets()`, `_calculate_carb_targets()`, `_calculate_fiber_targets()`, `_calculate_fat_targets()` — all removed; corresponding fields removed from MealPlanTargets; dead calls removed from MealPlanTargets constructor
- [x] Remove unreachable snack branches from `_diet_fallback_chain()` — `"Morning_Snack"` and `"Evening_Snack"` removed from breakfast condition
- [x] Backend syntax verified clean after dead code removal; backend restarted successfully

**Session findings:**
- `ctx.protein_targets`, `ctx.carb_targets`, `ctx.fiber_targets`, `ctx.fat_targets` were set on MealPlanTargets but NEVER READ in the generation loop — confirmed before removing
- Patient auth endpoint is `/api/v1/auth/token` with form-data (not JSON), not `/api/v1/auth/login` — noted for future verification scripts
- Diet plan endpoint is `/api/v1/diet-plans/my-plan` (not `/diet-plans/current`)
- Playwright MCP was not available for browser E2E; API verification confirmed plan structure correct
- Browser rendering verification (3 meal slots visible, no snack slots) deferred — not doable without Playwright

**Success criteria:** New plan structure verified correct ✅. Teaser updated ✅. Dead code removed ✅. No regressions ✅.

---

### SESSION 13 — Rating System Fix + Meal Detail Redesign
**Type:** Foundation + UI  
**Status:** COMPLETE (2026-06-02)  
**Dependencies:** Session 11 (dishes[] structure) ✅  
**Goal:** Wire rating endpoints to correct food_ids and redesign meal detail screen.

Tasks:
- [x] Audit: backend `meal_ratings` table has `food_item_id` (non-nullable FK) — no migration needed
- [x] Audit: `MealRateRequest` schema requires `food_item_id` — endpoint already correct
- [x] Audit: `services/progress.ts` `rateMeal()` already passes `food_item_id` — service layer correct
- [x] Root bug found: `meal-detail.tsx` read `meal?.food_id` (legacy top-level, always null after Session 11)
- [x] Added `Dish` interface and `dishes?: Dish[]` to `types/index.ts`
- [x] Full redesign of `meal-detail.tsx`: per-dish cards with staggered entry animation, per-dish rating buttons wired to correct `food_item_id`, per-dish expandable ingredients section with proportional labels, combined nutrition summary, "I Had This" with 1.4s success state before back navigation
- [x] Verified: 2 ratings saved to DB with correct `food_item_id` (3706 and 276), `patient_id=5` (Priya)

**Session findings:**
- `recommendation_id` is null on all meal objects in current plan response — ratings work correctly via `(patient_id, food_item_id)` but the upsert unique constraint may not deduplicate when `recommendation_id=NULL` (PostgreSQL NULL semantics). Low severity — flag for Session 16 schema fix.
- `services/progress.ts` has its own `MealRating` type (subset of `types/index.ts` version — missing `patient_id`). Using service type in meal-detail.tsx to match `getMyRatings` return type.
- Ingredients are embedded per dish in dishes[].ingredients (added in last task of this session) — each dish card has its own independent INGREDIENTS expandable toggle; tapping one expands only that dish.

**Resumed verification (Session 14 start):** Plan regenerated for Priya — all 7×3=21 meals confirmed, every dish in every meal has non-zero ingredient count (Breakfast: 2 dishes 8+1 ing; Lunch: 4 dishes 5+3+4+1 ing; Dinner: 4 dishes verified). Browser visual: 4 dish cards visible on Lunch detail, each card has own INGREDIENTS toggle that expands independently, 👍 👎 on all 4 cards, combined nutrition summary (528 kcal, 44g P, 48g C, 23g F, 19g Fi) at bottom.

**Success criteria:** Ratings save with correct food_item_id ✅. DB confirmed 2 rows, 0 null food_item_ids ✅. TypeScript clean in meal-detail.tsx ✅. Browser E2E: all 5 UI checks pass ✅.

---

### SESSION 14 — Ingredient Nutrition Chain (Tasks 2–5)
**Type:** Foundation  
**Status:** COMPLETE (2026-06-02)  
**Dependencies:** Session 10 schema (tables already existed, empty)  
**Goal:** Populate ingredients master table with names + LLM-estimated nutrition; link all recipes via recipe_ingredients.

Tasks:
- [x] Task 1 — Audit: food_items stores per-serving nutrition (manually entered, not calculated); 950 unique ingredient names in JSONB; Session 10 tables existed but empty; no IFCT2017 locally; Ollama not running
- [x] Task 2 — Alembic migration d5e6f7a8b9c0: ALTER ingredients (add name_normalized, unit_weight_g; make 5 nutrition cols nullable); add nutrition_source to food_items (default 'manual')
- [x] Task 3 — Seeded 950 unique ingredient names from JSONB into ingredients table (source='pending', nutrition=NULL)
- [x] Task 4 — LLM nutrition estimation via llama-server (gemma-4-E4B-it-Q4_K_M, --reasoning off, port 11434); batches of 20; 846/950 filled (89.2%); 104 NULL = ingredient names with embedded measurements (data quality artifact); source='estimated_llm'
- [x] Task 5 — Linked all JSONB ingredients to recipe_ingredients: 18,248 rows, 100% match rate; skipped zero-quantity entries (ck_ri_quantity_positive constraint); food_items.ingredients JSONB preserved as fallback
- [x] Added nutrition_source column to FoodItem ORM model
- [x] Task 6 (recalculation) deferred to Session 15 per product owner decision

**Session findings:**
- Session 10 tables already existed with richer schema than spec (has name_hindi, sodium/iron/calcium). Kept all, added missing cols.
- llama.cpp at C:\llama has gemma-4-E4B-it-Q4_K_M.gguf (4.97GB). Server mode: `llama-server.exe -m ... --port 11434 --reasoning off --gpu-layers 99`. OpenAI-compatible `/v1/chat/completions`.
- 104 NULL ingredients are measurement-phrases ("1/2 tablespoons X", "To 3 dry red chilli") — not real ingredient names, artifact of source dataset.
- 100% recipe_ingredients match because all 950 names in lookup were seeded from the same JSONB source.
- ORM models for Ingredient and RecipeIngredient not yet added to db_models.py — needed for Session 15 Task 6.

**Success criteria:** ingredients table populated ✅ (846/950 with nutrition). recipe_ingredients linked ✅ (18,248 rows, 100% match). Migration applied ✅. nutrition_source column live ✅.

---

### SESSION 14 — Recipe Nutrition Recalculation (DEFERRED → Session 15)
**Type:** Execution (/goal acceptable)  
**Status:** NOT STARTED — deferred per product owner  
**Dependencies:** Session 14 Tasks 2–5 complete ✅  
**Goal:** Build recipe_ingredients table and recalculate food_items nutrition from ingredient level.

Tasks:
- [ ] Map existing food_items ingredients JSONB to recipe_ingredients rows
- [ ] Match ingredient names to ingredients table (fuzzy match where needed)
- [ ] Flag unmatched ingredients for doctor review
- [ ] Recalculate cal/protein/carbs/fat/fiber for each recipe from ingredient data
- [ ] Compare recalculated vs original values — flag large discrepancies
- [ ] Mark recipes with verified ingredient matches as is_verified = true
- [ ] Keep old nutrition values as fallback for unmatched recipes

**Success criteria:** recipe_ingredients populated. Verified recipes have nutrition calculated from INDB data. Unverified recipes still work with old data.

---

### SESSION 15 — Nutrition Chain Verification + IFCT Import Fix
**Type:** Verification + Data Fix  
**Status:** COMPLETE ✅  
**Dependencies:** Session 14 complete  
**Goal:** Confirm the full ingredient → recipe → meal → day total math is correct.

Tasks:
- [x] Identify root cause of 583-recipe reversion: IFCT matched measurement-phrase ingredient names ("1/2 tablespoons mustard seeds" with quantity_g=80g) → inflated per-dish calories → 582 recipes >1500 kcal outlier-reverted
- [x] Fix: added `ARTIFACT_RE` filter in `scripts/import_ifct.py` to skip ingredients whose names start with digits/fractions or contain tablespoon/teaspoon/tbsp/tsp/cup/ml/kg (deliberately excludes "gram" to preserve Bengal gram, Black gram, Green gram legume names)
- [x] Reset 15 dirty IFCT2017 ingredients (measurement-phrase artifacts) back to NULL nutrition + source='LLM'
- [x] Re-ran `import_ifct.py --write` → 88 clean matches (vs 95 before; 15 artifacts excluded, some freed IFCT slots now matched to legitimate ingredients)
- [x] Re-ran `recalculate_recipe_nutrition.py` → 2101 calculated, 41 manual (vs 1524/618 before fix)
- [x] Re-ran `_fix_outliers.py` → 582 quantity-error recipes (bad quantity_g data, e.g. 8000g makhana, 1600g cashews) reverted to manual — these are pre-existing batch data errors unrelated to IFCT
- [x] Sanity check: 0 outliers in calculated set (range 50–1499 kcal ✅)
- [x] Priya's existing plan verified: Lunch = 528 kcal (4 dishes: Dondakkai Puli, Chana Masala, Cabbage Foogath, Chaas) — calculated dishes within valid range, generator scales manual entries correctly

**Final state:** calculated=1519, manual=623 (582 of manual have bad quantity_g data — quantity_g column needs cleanup in future session to recover these)

**Success criteria:** Nutrition chain verified end to end. No impossible values in calculated set. ✅

---

### SESSION 16 — Food Database Pipeline Fix + Doctor Recipe Controls
**Type:** Execution  
**Status:** COMPLETE ✅ (2026-06-04)  
**Dependencies:** Session 11 complete (dishes[] structure exists)  
**Goal:** Fix food database pipeline (global recipe leak, AI dedup) + give doctor dish-level editing.

Tasks:
- [x] Task 1 — Audit: mapped custom meal add, AI lookup, and recipe naming flows
- [x] Task 2 — Skipped: "Doctor2 Private Dal" naming artifacts are manual test data, no code fix needed; IDs 3697–3715 logged to KNOWN ISSUES
- [x] Task 3 — Fix custom meal pipeline: new `POST .../plan/meals/{date}/{meal_type}/add` endpoint; default path writes only to JSONB (no food_items row); add_to_library=True creates food_item with submitted_for_review=True. Migration e6f7a8b9c0d1 adds submitted_for_review column. Frontend AddMealForm updated to call new endpoint.
- [x] Task 4 — Fix AI lookup dedup: add_recipe endpoint now checks for exact name match before creating; returns existing record if found. Verified with "Palak Paneer Test S16" test.
- [x] Task 5 — Recipes page: snack tabs already absent (no code change); added Verified/Unverified filter — backend is_verified query param + frontend three-button toggle
- [x] Task 6 — PATCH endpoint for dish-level editing: swap/remove/add actions; recalculates slot totals; records DoctorMealOverride with patient_id + override_date + meal_type; backfills recommendation_id on slot
- [x] Task 7 — Doctor dashboard dish cards: DishCard + RecipeSearchModal components added to PlanTab.tsx; per-dish swap/remove/add UI wired to PATCH endpoint; fallback for legacy meals without dishes[]
- [x] Task 8 — Regression: 21 slots ✅, dishes[] in all ✅, meal log 200 ✅, food_items count stable ✅, override rows have full traceability ✅

**Session findings:**
- `browse_recipes` endpoint previously only returned verified items (is_verified=True hardcoded). Changed to return all items when no is_verified filter provided — more consistent with doctor library use case.
- Priya's plan had pre-existing orphan Palak Paneer Lunch entry (0 dishes, no food_id) from prior session testing — removed during regression cleanup.
- Two pre-existing TypeScript errors logged to KNOWN ISSUES (MealEntry.id, submit_to_global).
- `submitted_for_review` column added to food_items via migration e6f7a8b9c0d1.
- Session 16 test data: food_items 2143 (2142 base + 1 dedup test record "Palak Paneer Test S16" at ID 3725).

**Success criteria:** Doctor can swap individual dishes ✅. Override tracking records food_ids ✅. Custom meals no longer leak to global food_items ✅.

---

### SESSION 17 — Doctor Meal Config Panel
**Type:** Execution (/goal acceptable)  
**Status:** NOT STARTED  
**Dependencies:** Session 16 complete  
**Goal:** Give doctor control over pool parameters and TDEE split per patient.

Tasks:
- [ ] New patient model fields: meal_split_override JSONB, pinned_dishes[], blocked_dishes[]
- [ ] New API endpoint: PATCH /doctor/patients/{id}/meal-config
- [ ] Doctor dashboard: Meal Config tab on patient detail
- [ ] TDEE split sliders (Breakfast %, Lunch %, Dinner %) — must sum to 85%
- [ ] Pin dish: search recipes, pin to always appear first in suggestions for this patient
- [ ] Block dish: search recipes, block from ever appearing for this patient
- [ ] Regenerate plan automatically when config saved
- [ ] Generator reads patient-level overrides before using defaults

**Success criteria:** Doctor can adjust TDEE split. Pinned dishes appear first. Blocked dishes never appear. Generator respects overrides.

---

### SESSION 18 — Medical Condition Tagging
**Type:** Execution (/goal for tagging run, manual for review UI)  
**Status:** NOT STARTED  
**Dependencies:** Tag schema locked (already done — see decision log above)  
**Goal:** Tag all 2,141 recipes for medical conditions and give doctors review UI.

Tasks:
- [ ] Add condition tag fields to food_items (avoid_tags[], prefer_tags[] — JSONB arrays)
- [ ] Write Gemma 4 8B local tagging script — analyze each recipe's ingredients and assign tags
- [ ] Run tagging on all 2,141 recipes — output confidence score per tag
- [ ] Use Claude API to review low-confidence and edge case tags
- [ ] Doctor dashboard: Recipe tag review queue — show AI-assigned tags, doctor can approve/correct
- [ ] Corrections update master food_items record immediately
- [ ] Generator: apply avoid_tags filtering before selecting dishes for a patient
- [ ] Generator: boost prefer_tags dishes in ranking for relevant conditions
- [ ] Test: diabetic patient no longer gets samosas or fried high-GI dishes

**Success criteria:** All recipes tagged. Diabetic patient gets filtered pool. Doctor can correct tags. Corrections persist.

---

### SESSION 19 — Adaptive Suggestion API
**Type:** Foundation (no /goal — architectural)  
**Status:** NOT STARTED  
**Dependencies:** Sessions 13–16 complete  
**Goal:** Build the on-demand multi-option generation and iterative calorie tracking API.

Tasks:
- [ ] New endpoint: GET /meal-plan/suggestions/{date}/{meal_type} — returns 3–4 dish options
- [ ] Options ranked by: patient condition tags, doctor pins, TDEE fit, variety (not already chosen this week)
- [ ] New endpoint: POST /meal-plan/confirm-choice — patient picks one, logged to DB
- [ ] GET /progress/today already returns calories.remaining — verify accuracy
- [ ] Suggestion engine sizes options to remaining daily budget after confirmed choices
- [ ] Confirm choice triggers next meal suggestions to update accordingly
- [ ] Doctor pin/block config influences suggestion ranking

**Success criteria:** Suggestions endpoint returns 3–4 options. Confirming a choice reduces remaining budget. Next suggestions adjust.

---

### SESSION 20 — Patient App Adaptive UI
**Type:** Execution (/goal acceptable)  
**Status:** NOT STARTED  
**Dependencies:** Session 19 complete  
**Goal:** Update patient app to show choice cards and real-time calorie tracking.

Tasks:
- [ ] Meals tab: replace static plan display with meal slot cards showing 3–4 options
- [ ] Each option card: dish name, macros, proportional ingredients, select button
- [ ] On selection: POST confirm-choice, calorie ring updates immediately
- [ ] Remaining budget shown prominently on Home tab
- [ ] Add Snack quick-log button to Home tab Quick Log section
- [ ] Snack log bottom sheet: common snack options + free entry
- [ ] Snack calories deduct from buffer in real time
- [ ] Week view updated to show chosen dishes (not suggestions) for past days

**Success criteria:** Patient can choose from options. Calorie ring reflects choices in real time. Snack quick log works.

---

### SESSION 21 — Doctor Weekly Patient Summary
**Type:** Execution (/goal acceptable)  
**Status:** NOT STARTED  
**Dependencies:** Session 20 complete  
**Goal:** Give doctor visibility into what patient actually chose and how they adhered.

Tasks:
- [ ] New API endpoint: GET /doctor/patients/{id}/weekly-summary
- [ ] Returns: what patient chose each day, calorie totals vs targets, buffer utilization, snack logs
- [ ] Doctor dashboard: new Weekly Summary tab on patient detail
- [ ] Show: chosen meals per day, adherence %, days over/under budget
- [ ] Alert indicators: patient consistently chose highest-calorie option (3+ days)
- [ ] Alert indicators: patient skipped logging (2+ days)

**Success criteria:** Doctor can see weekly patient choices. Alerts surface meaningful patterns.

---

### SESSION 22 — Frontend Display Updates
**Type:** Execution (/goal acceptable)  
**Status:** NOT STARTED  
**Dependencies:** Sessions 14–16 complete  
**Goal:** Update all display layers to macro-only with proportional labels.

Tasks:
- [ ] Patient app meal detail: remove gram quantities, show macros prominently
- [ ] Add proportional ingredient labels (map gram ranges to prose labels)
- [ ] Doctor dashboard plan view: same macro-only display for consistency
- [ ] Shopping list: ingredient names only — remove all quantity columns
- [ ] Beverage category UI: separate section in patient app and doctor dashboard
- [ ] Accompaniments shown as separate sub-slot (not concatenated with main dish name)

**Success criteria:** No gram quantities shown anywhere. Proportional labels render. Shopping list names-only. Beverages separate.

---

### SESSION 23 — Full System Verification
**Type:** Verification  
**Status:** NOT STARTED  
**Dependencies:** All previous sessions complete  
**Goal:** End to end audit of complete system before design phase begins.

Tasks:
- [ ] Full critical path: register → onboard → get suggestions → choose meals → doctor reviews → adjusts config → patient sees updated suggestions
- [ ] Diabetic patient gets correct filtered suggestions
- [ ] Doctor TDEE override changes patient's meal sizing
- [ ] Rating system collects real thumbs-up/down data
- [ ] Override tracking records real food_ids
- [ ] Nutrition chain: ingredient edit propagates to meal plan
- [ ] Weekly summary shows accurate patient choices
- [ ] All P0 and P1 issues from known issues list resolved

**Success criteria:** All 23 session tasks verified. System ready for design phase.

---

## AUDIT REPORTS INDEX

| Report | Location | Session |
|--------|----------|---------|
| Meal system investigation | `docs/MEAL_PLAN_INVESTIGATION.md` | Session 7 |
| Meal system audit (variety, conditions, depth) | `docs/MEAL_SYSTEM_AUDIT_SESSION7.md` | Session 7 |
| Database full audit | `docs/DATABASE_AUDIT_SESSION8.md` | Session 8 |
| Meal structure audit (dishes[] finding) | `docs/MEAL_STRUCTURE_AUDIT.md` | Session 8 |

---

## SESSION HISTORY SUMMARY

| Session | Key Outcomes |
|---------|-------------|
| 1 | Web bundle fixed (expo-linear-gradient), Playwright MCP installed, Phase 1 onboarding confirmed working |
| 2 | Doctor dashboard 422 fixed, week view snacks fixed, shopping list names fixed, progress tab re-fetch fixed |
| 3 | Meal detail ingredients fixed, meal logging 422 fixed across 6 files, home tab dynamic meal slots, streak bug fixed |
| 4 | Freemium teaser built, doctor discovery unblocked, onboarding persistence added, three-state code lifecycle implemented, token_1 moved to activation |
| 5 | SQLAlchemy ambiguous FK fix, Zustand ESM Metro fix, CHECK 1 (ASHOK2 reserved) and CHECK 3 (Priya resumes) verified |
| 6 | Login race condition fixed, all 6 lifecycle checks verified, full regression sweep passed, doctor dashboard token_1 display confirmed |
| 7 | 326 recipe duplicates fixed, variety/diet/region filtering audited, medical condition filtering confirmed absent, recipe depth gaps quantified |
| 8 | Full database audit (6k recipes myth confirmed — only 2,141 exist), meal structure audit (dishes as concatenated string confirmed), rating system silent failure discovered |
| 9 | P0 data fixes: 6 recipes with 40,000g ingredient amounts corrected + "Gm " prefix cleaned; 18 beverages moved to correct slot_type (actual scope wider than expected 8); is_verified badge added to doctor recipe cards; serving_weight_g + sodium_per_serving added to recipe creation form and backend schema |
| 10 | Schema designed and approved: 5 new tables (ingredients, recipe_ingredients, beverages, patient_meal_config, patient_dish_preferences) + dishes[] JSONB spec for recommendations.meals; migration written (c2d3e4f5a6b7) but not run; product owner approved with 3 changes (glycemic_index removed, 2 CHECK constraints added) |
| 11 | Migration run (all 5 tables confirmed); PatientMealConfig ORM added; meal_generator rewritten: snacks removed, effective_tdee=TDEE×0.85, patient_meal_config override, dishes[] with food_id per slot; validator fixed (35→21); all 4 verification checks PASS, all regression checks PASS |
| 12 | Dead code removed from meal_generator.py (5 _calculate_*_targets methods + 4 MealPlanTargets fields + snack branches in _diet_fallback_chain); MEAL_ORDER updated to 3 meals in 5 patient app files; TEASER_MEALS reduced to 3 entries; API verified: 21 slots, 0 snacks, dishes[] + food_id in all meals. Post-session fix: meals_per_day DB default corrected (5→3), 6 existing patients migrated via SQL, progress_service fallback corrected, dead "5 meals (with snacks)" onboarding option removed |
| 13 | Rating system bug fixed (meal.food_id was always null — moved to dishes[].food_id); Dish type added to types/index.ts; meal-detail.tsx fully redesigned: per-dish cards with staggered animation, per-dish thumbs up/down wired to correct food_item_id, per-dish expandable ingredients with proportional labels, combined nutrition summary, success state on "I Had This"; DB confirmed: ratings save with correct food_item_id; E2E browser verification passed (4 cards, per-dish ingredients, thumbs up/down, combined summary) |
| 14 | Alembic migration d5e6f7a8b9c0: ALTER ingredients (name_normalized, unit_weight_g, nullable nutrition), add nutrition_source to food_items; seeded 950 ingredient names; LLM nutrition estimation via llama.cpp (gemma-4-E4B-it-Q4_K_M, --reasoning off) — 846/950 filled (89.2%), 104 NULL = measurement-phrase artifacts; linked 18,248 recipe_ingredients rows (100% match); Task 6 recalculation deferred to Session 15 |
| 15 | Fixed IFCT measurement-phrase matching bug (added ARTIFACT_RE filter to import_ifct.py); reset 15 dirty IFCT2017 ingredients; re-imported 88 clean IFCT matches; recalculated → 2101 calculated, 41 manual; re-ran outlier reversion → 1519 calculated, 623 manual (582 reverted = bad quantity_g batch data errors, not IFCT issue); 0 outliers in calculated set (range 50–1499 kcal); Priya lunch verified at 528 kcal |
| 16 | Fixed custom meal pipeline (JSONB-only by default, no global food_items leak); added submitted_for_review column (migration e6f7a8b9c0d1); added dedup to add_recipe endpoint; added is_verified filter to browse_recipes; built PATCH endpoint for dish-level swap/remove/add with DoctorMealOverride traceability + recommendation_id backfill; built dish card UI (DishCard + RecipeSearchModal) in PlanTab.tsx; all regression checks pass |

---

## IMPORTANT TECHNICAL NOTES

- **PowerShell only** for running Python on Windows — bash fails on Windows venv
- **Rate limiter:** login endpoint limited to 5 per 15 min — restart backend to clear during testing
- **Docker Desktop** must be running before starting backend (PostgreSQL in container)
- **Patient token** stored in localStorage as `mitihar_access_token`
- **Doctor login** uses `POST /api/v1/auth/doctor/login` NOT `/api/v1/auth/token`
- **Onboarding fields:** activity_level uses short codes (e.g. "LA" not "Lightly Active")
- **Meal type strings** must be exact: "Breakfast", "Lunch", "Dinner" — snack meal types fully removed in Sessions 11–12
- **meals_per_day column default was 5** from original schema — corrected to 3 in Session 12 post-fix (db_models.py + progress_service fallback). All 6 existing patients migrated via direct SQL. If meal structure changes again, search for hardcoded `5` in these two files plus any onboarding UI options.
- **Zustand v5** — always resolves to CJS build on web (metro.config.js override in place)
- **food_id now stored in dishes[]** — each meal slot in recommendations.meals has `dishes` array containing `food_id` (FoodItem.id PK), `recipe_name`, `slot_type`, per-dish macros. Plans without `dishes` key are legacy (pre-Session 11), shown read-only.
- **Generator produces 21 meal slots** — 3 meals × 7 days. `EXPECTED_MEAL_COUNT = 7 * 3` in diet_plans.py. Update constant there if structure changes again.
- **patient_id must be int in generator** — `user_data["id"]` is a string from the API route. `int(patient_id)` cast is required before PatientMealConfig query. asyncpg does not implicit-cast varchar to integer column (raises UndefinedFunctionError).
- **Patient auth endpoint** — `/api/v1/auth/token` with `application/x-www-form-urlencoded` body (not JSON). Username/password as form fields.
- **Diet plan endpoint** — `/api/v1/diet-plans/my-plan` returns current patient plan. Not `/diet-plans/current`.
- **DEFAULT_SPLIT** constant at module level in meal_generator.py: `{"Breakfast": 0.25, "Lunch": 0.35, "Dinner": 0.25}`. Used when no PatientMealConfig override exists for patient.
- **ingredients table** — 950 rows (846 with LLM-estimated nutrition, 104 NULL = measurement-phrase names). Unique constraint on (name, source). name_normalized = lowercase+stripped for matching. source='estimated_llm' for Gemma-estimated values.
- **recipe_ingredients table** — 18,248 rows linking all food_items to ingredients. quantity_g has CHECK > 0 (ck_ri_quantity_positive). food_items.ingredients JSONB preserved as fallback.
- **nutrition_source column** on food_items — 'calculated' for 1519 recipes (recalculated from ingredient chain via IFCT2017 + LLM values), 'manual' for 623 (26 have no recipe_ingredients, 582 have bad quantity_g batch data errors, 15 low coverage). Calculated set: 0 outliers, range 50–1499 kcal.
- **IFCT2017 import** — 88 ingredients upgraded (scripts/import_ifct.py). ARTIFACT_RE filter added to skip measurement-phrase ingredient names (e.g. "1/2 tablespoons mustard seeds"). Blocklist in place for 4 known wrong matches. Re-run with `python -m scripts.import_ifct --write` after any ingredient additions.
- **582 manual recipes with bad quantity_g** — these recipes have pre-existing batch data entry errors (e.g. quantity_g=8000 for makhana, 1600 for cashews). They are correctly labelled 'manual' with their original hand-entered cal_per_serving values. Future session: audit quantity_g outliers and correct them to recover these recipes for calculation.
- **llama.cpp** at C:\llama — `llama-server.exe -m C:\llama\gemma-4-E4B-it-Q4_K_M.gguf --port 11434 --gpu-layers 99 --reasoning off`. OpenAI-compatible API at `/v1/chat/completions`. Model: Gemma 4 E4B Q4_K_M (4.97GB, fits RTX 4050 6GB).
- **Ingredient ORM models** — `Ingredient` and `RecipeIngredient` ORM classes added to db_models.py in Session 15.
- **submitted_for_review column** — added to food_items (migration e6f7a8b9c0d1, default=False). Set True when doctor explicitly submits a custom recipe to the admin approval queue.
- **Custom dish JSONB path** — `POST /doctor/patients/{id}/plan/meals/{date}/{meal_type}/add` writes directly to recommendations.meals JSONB. Default: food_id=null, is_custom_override=True, no food_items row created. add_to_library=True: creates food_items with submitted_for_review=True.
- **Dish-level PATCH** — `PATCH /doctor/patients/{id}/plan/meals/{date}/{meal_type}/dishes/{dish_index}` — actions: swap/remove/add. Recalculates slot totals, rebuilds Menu Names, records DoctorMealOverride with patient_id + override_date + meal_type, backfills recommendation_id onto slot.
- **add_recipe dedup** — `POST /doctor/recipes` now checks LOWER(TRIM(recipe_name)) match before creating. Returns existing record if found (status 201, same body — idempotent from caller perspective).
- **browse_recipes change** — previously hardcoded is_verified=True filter (only returned verified items). Now returns all items by default; use ?is_verified=true/false to filter.
- **Meal log endpoint** — correct path is `POST /api/v1/progress/log/meal` (not /meal-log). Note for future regression scripts.
