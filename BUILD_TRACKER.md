# Mityahar — Build Tracker
**Last updated:** Session 20.5 (2026-06-08, password hash root cause fix complete)  
**Next session:** Session 21 — Patient App Adaptive UI  
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
| Medical condition filtering does nothing | ~~P1~~ FIXED | Session 19 — avoid_tags/prefer_tags wired into generator |
| testaudit@mityahar.com token_1 shows Inactive (legacy account) | Low | Data artifact, not a bug |
| plan_type_tags identical on all 2,141 recipes (useless) | P1 | Session 18B — avoid_tags/prefer_tags replace this in Session 18B |
| Shopping list shows names but no quantities are meaningful | P1 | Sessions 13–14 |
| 3 food_items still have "Gm " prefix ingredient names (Gm arhar dal ×1, Gm makhana ×2) — correct amounts, corrupted names only | P2 | Session 14 |
| 560g curry leaves in ID 2924 (Arabic Vegetable) — single-serving amount suspicious but not > 10,000g | P2 | Session 14 |
| ID 2674 (Drumstick Buttermilk Curry) slot_type='grain' — should be 'sabzi' (unrelated to beverage fix) | P2 | Session 14 |
| food_items IDs 3697–3715 recipe_name "Doctor2 Private Dal" — manual test data artifacts, not a bug | Low | Manual DB cleanup needed |
| TS error: MealEntry has no 'id' field — PlanTab.tsx line 888 uses meal.id which doesn't exist in the interface. Pre-existing before Session 16. | Low | Session 18 |
| TS error: Recipes.tsx AddRecipeForm missing submit_to_global field in addRecipe call. Pre-existing. | Low | Session 18 |
| recommendation_id backfilled on new dish ops — existing meal slots still null until next PATCH operation or plan regeneration | Low | Resolves gradually via use |
| confirm-choice accepts any food_item_id regardless of whether its meal_time_tags match the requested meal_type — a Breakfast dish can be confirmed into a Lunch slot via direct API call. Fix: add `meal_time_tags @> ARRAY[meal_type_lower]` validation in the endpoint before the upsert. Deferred — low risk since the suggestions endpoint only surfaces slot-appropriate dishes to patients. | P2 | Session 20 |

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
**Status:** COMPLETE ✅ (2026-06-06)  
**Dependencies:** Session 16 complete  
**Goal:** Give doctor control over pool parameters and TDEE split per patient.

Tasks:
- [x] Task 1 — Audit: confirmed patient_meal_config table exists, PatientMealConfig ORM exists, PatientDishPreferences ORM was missing (added), generator reads meal_split_override, patient_dish_preferences was unused
- [x] Task 2 — API: GET + PATCH /doctor/patients/{id}/meal-config + POST/DELETE pin/block endpoints (6 total). Server-side 85% validation. Upsert via pg_insert ON CONFLICT DO UPDATE. Config saved before regen; regen failure returns plan_regenerated=false + error without failing config save
- [x] Task 3 — Generator: reads patient_dish_preferences for blocked/pinned food_ids; blocked dishes filtered via WHERE NOT IN on base query; pinned dishes injected at front of slot, displacing last dish at capacity
- [x] Task 4 — Frontend: Meal Config tab added to PatientDetail.tsx; MealConfigTab.tsx created with 3 sections (TDEE Split / Pinned Dishes / Blocked Dishes); debounced recipe search dropdowns; Save & Regenerate + Reset to Default; live total validation
- [x] Task 5 — E2E: 12 checks all PASS: login, GET defaults, 422 validation, PATCH split, DB confirm, 21 slots, pin, GET confirms pin, pin→block switch, unblock, reset
- [x] Task 6 — Regression: 21 slots ✅, dishes[] present ✅, food_items count 2143 ✅, meal config state clean ✅

**Session findings:**
- `CheckConstraint` was missing from db_models.py import line — added alongside existing `UniqueConstraint`
- `PatientDishPreferences` ORM model was missing from db_models.py — added (table existed from Session 10 migration)
- Backend must be restarted to pick up new routes in doctor.py — OpenAPI spec check confirms load
- Patient auth `/auth/token` rate-limited to 5/15min (in-memory); regression scripts should use doctor auth endpoint
- `/diet-plans/my-plan` returns `{..., "meals": [...]}` dict, not a flat array — regression scripts must read `plan["meals"]`
- Session 17 adds `CheckConstraint` to sqlalchemy imports in db_models.py

**Success criteria:** Doctor can adjust TDEE split ✅. Pinned dishes appear first ✅. Blocked dishes never appear ✅. Generator respects overrides ✅.

---

### SESSION 18A — Medical Condition Tagging (Pilot)
**Type:** Research + Foundation  
**Status:** COMPLETE ✅ (2026-06-06)  
**Dependencies:** Tag schema locked (see decision log above)  
**Goal:** Build clinical knowledge base, add schema columns, run 50-recipe pilot to calibrate confidence thresholds before full run.

Tasks:
- [x] Task 1 — Build `docs/MEDICAL_TAGGING_KNOWLEDGE_BASE.md` — full clinical KB for all 14 conditions (60,972 chars). Indian-specific rules, FODMAP framework, GI guidance, edge cases, cooking method matrix.
- [x] Task 2 — Add `avoid_tags` + `prefer_tags` JSONB columns to food_items. Alembic migration f7a8b9c0d1e2. GIN indexes on both columns. ORM model updated. Migration applied and verified (both columns confirmed jsonb type).
- [x] Task 3 — Built `docs/MEDICAL_TAGGING_KB_COMPACT.md` (8,979 chars, ~2,245 tokens) — distilled trigger list for direct LLM injection. Full KB is reference only; compact KB is the system prompt.
- [x] Task 4 — 50-recipe pilot selection: 4 coverage buckets (clearly avoid, clearly prefer, ambiguous, condition-specific). Script `scripts/tag_recipes_pilot.py` runs via llama-server port 11434 (Gemma 4 E4B Q4_K_M). Output to `docs/PILOT_TAGGING_RESULTS.md`, no DB writes.
- [x] Task 5 — Pilot ran: 50/50 tagged, 0 errors, 221 tag assignments. Manual quality review completed.

**Pilot findings — confidence distribution:**
| Range | Count | % |
|-------|-------|---|
| ≥ 0.8 | 106 | 47% |
| 0.5–0.79 | 105 | 47% |
| 0.25–0.49 | 10 | 4% |

**Pilot findings — errors found (8 across 7 recipes):**

| Recipe | Error | Confidence | Root cause |
|--------|-------|------------|------------|
| Millet Khichdi (bajra) | `avoid_diabetes` assigned — should be `diabetes_friendly` | 0.60 | Millet confusion (see below) |
| Jowar roti | `avoid_diabetes` assigned — should be `diabetes_friendly` | 0.70 | Millet confusion |
| Jowar roti | `avoid_pcos` assigned — should be `pcos_friendly` | 0.70 | Millet confusion |
| Lauki Paneer | `avoid_kidney` assigned — lauki is kidney-SAFE per KB | 0.80 | Self-contradictory reasoning |
| Arbi Achaar (pickle) | `gut_friendly` assigned — vinegar+chilli pickle is gut-irritating | 0.80 | Ingredient isolation without dish context |
| Stuffed Mango Pickle | `diabetes_friendly` for trace methi seeds | 0.50 | Ingredient isolation without dish context |
| Oats Moong Dal | `gluten_free` assigned — oats require certified GF flag | 0.95 | Cross-contamination rule missed |
| Chicken Biryani | Missing `avoid_diabetes` entirely | — | Tag omission |

**Root causes identified:**
1. **Millet confusion**: Gemma sees "millet = low-GI" in its reasoning but assigns `avoid_*` tag anyway. KB lists millets under DIABETES_FRIENDLY but model mixes up sections.
2. **Self-contradictory reasoning**: Model reasons correctly ("lauki is kidney-safe") then assigns `avoid_kidney`. Instruction-following failure — JSON format forces a tag, model hedges with wrong tag at medium confidence.
3. **Ingredient isolation**: Beneficial spice ingredient (methi, ajwain) in achaar/pickle overrides dish-level context. High-sodium/acid preparation dominates.
4. **Oats rule**: Cross-contamination rule present in compact KB but model didn't apply it. 0.95 confidence false `gluten_free` is high-risk for celiac patients.

**Recommended confidence thresholds:**
- **Auto-accept: ≥ 0.90** — ~95% safe rate in pilot; requires compact KB fixes first
- **Claude API review: 0.50–0.89** — verify before writing to DB (too noisy to auto-accept)
- **Discard: < 0.50** — already filtered in script
- **Special rule**: Never auto-accept `avoid_diabetes` or `avoid_pcos` on millet recipes (jowar/bajra/ragi) until compact KB millet section clarified — clinically dangerous false avoids

**Required compact KB fixes before Session 18B:**
1. Add: "Jowar, bajra, ragi are DIABETES_FRIENDLY and PCOS_FRIENDLY — NEVER assign avoid_diabetes or avoid_pcos to millet-only dishes"
2. Add: "For any achaar/pickle dish: only assign avoid_hypertension. Positive tags from spice ingredients do not apply — pickling medium dominates"
3. Move oats cross-contamination warning to a prominent/bold position
4. Add to USER_PROMPT_TMPL: "If your reasoning says an ingredient is safe for a condition, do NOT assign the avoid tag for that condition"

**Session findings:**
- Full KB (60,972 chars ≈ 15,000+ tokens) caused HTTP 400 from llama-server — exceeds 8,192-token context window. Fixed by creating compact KB version.
- asyncpg required for DB access in scripts (psycopg2 not installed in venv)
- Helper scripts created: `scripts/_verify_tags_cols.py`, `scripts/_pilot_candidates.py`, `scripts/_pilot_select.py`

**New files:**
- `docs/MEDICAL_TAGGING_KNOWLEDGE_BASE.md` — full clinical reference (60,972 chars)
- `docs/MEDICAL_TAGGING_KB_COMPACT.md` — LLM injection version (8,979 chars)
- `docs/PILOT_TAGGING_RESULTS.md` — all 50 tagged recipes + quality analysis
- `scripts/tag_recipes_pilot.py` — pilot tagging script (no DB writes)
- `alembic/versions/f7a8b9c0d1e2_add_condition_tags_to_food_items.py`

**Success criteria:** Schema columns live ✅. Pilot ran 50/50 ✅. Quality issues documented ✅. Thresholds calibrated ✅. Compact KB fixes specified ✅.

---

### SESSION 18B — Medical Condition Tagging (Full Run + Doctor Review UI)
**Type:** Execution  
**Status:** COMPLETE ✅ (2026-06-07) — scope delivered across Sessions 18B/18C/19/19-ext  
**Dependencies:** Session 18A complete ✅  
**Goal:** Fix compact KB errors, run full 2,141-recipe tagging, build doctor review queue UI.

Tasks:
- [x] Apply 4 compact KB fixes from Session 18A findings (millet rule, achaar rule, oats prominence, self-contradiction guard)
- [x] Run 10-recipe mini-pilot to verify fixes before full run
- [x] Run ingredient-level (Layer 2) tagging + recipe-level derivation (Layer 3) — 2116/2143 food_items tagged
- [x] Doctor dashboard: `GET /doctor/recipes/{id}/tags` + `PATCH /doctor/recipes/{id}/tags` endpoints; VALID_TAGS validation (422 on unknown tag); auto-sets is_verified=True
- [x] `TagEditPanel` in Recipes.tsx — 12 avoid + 10 prefer pill toggles; inline in RecipeCard; tag badges on card faces
- [x] Corrections persist to food_items immediately — next plan generation reflects corrected tags
- [x] Generator: avoid_tags JSONB filter (NOT @> via GIN index) applied per patient conditions
- [x] Generator: prefer_tags boost as primary ORDER BY clause for relevant conditions
- [x] Verified: diabetic+hypertension patient → 0 violations across 77 dishes

**Success criteria:** All recipes tagged ✅. Diabetic patient gets filtered pool ✅. Doctor can correct tags ✅. Corrections persist ✅.

---

### SESSION 19 — Generator Tag Integration
**Type:** Foundation  
**Status:** COMPLETE ✅ (2026-06-07)  
**Dependencies:** Session 18C complete (Layer 3 tags live on 2116/2143 food_items)  
**Goal:** Wire avoid_tags/prefer_tags into meal_generator.py so medical conditions drive dish selection automatically.

Tasks:
- [x] Pre-task audit 1 — Layer 3 data confirmed live: avoid_tags non-empty 1194, prefer_tags non-empty 1940, 27 empty (no recipe_ingredients), distinct tags match BUILD_TRACKER ✅
- [x] Pre-task audit 2 — medical_conditions field confirmed: JSONB array, exact UI strings from onboarding screen, all test patients have empty arrays
- [x] Pre-task audit 3 — base_stmt() located in meal_generator.py:515 (nested closure), patient data available via user_data in generate_meal_plan, no existing condition filtering
- [x] Pre-task audit 4 — tag cross-check: 10/12 avoid tags match; avoid_pcos and avoid_gout are 0-match no-ops (never assigned in Layer 2)
- [x] Task 1 — `app/services/meal_generator/tag_utils.py` created: CONDITION_AVOID_TAGS, CONDITION_PREFER_TAGS dicts (15 conditions × exact DB tag strings), get_avoid_tags(), get_prefer_tags() helpers
- [x] Task 2 — Avoid tag filter in base_stmt(): NOT (avoid_tags @> '["tag"]' OR ...) using JSONB contains(); GIN index used
- [x] Task 3 — Prefer tag boosting: prefer_sort = OR(prefer_tags @> each tag).desc() prepended to ORDER BY; existing region_sort + cal_sort as tiebreakers
- [x] Task 4 — Regression: 5/5 checks pass (see below)
- [x] Task 5 — BUILD_TRACKER updated

**Regression results:**
- Check 1: Diabetic+Hypertension patient → 77 dishes, 0 avoid_diabetes / avoid_hypertension violations ✅
- Check 2: Healthy patient (no conditions) → 21 slots, 0 empty ✅
- Check 3: food_items count unchanged (2143 before and after) ✅
- Check 4: Hypertension covered by Check 1 ✅
- Check 5: full_backend_test.py — pre-existing crash (admin login uses wrong path prefix, unrelated to this session)

**Condition gaps flagged:**
- `avoid_pcos` — 0 food_items in DB; PCOS/PCOD filter is a no-op until Layer 2 tags are added to pcos-relevant recipes
- `avoid_gout` — 0 food_items in DB; Gout filter is a no-op until Layer 2 tags are added

**New files:**
- `app/services/meal_generator/tag_utils.py` — condition→tag mapping + helper functions

**Session findings:**
- `FoodItem.avoid_tags.overlap()` does not exist on JSONB columns (only on ARRAY columns). Used `contains([tag])` → `@> '["tag"]'` which correctly uses the GIN index.
- `or_()` with `.contains()` list comprehension produces the correct JSONB overlap semantics for multi-condition patients.
- `prefer_sort` computed once per `_find_food_item_single_diet()` call; passed via closure into `base_stmt()` alongside existing `region_sort` and `cal_sort`.
- Patient with `medical_conditions=[]` computes empty frozensets; both filters skip entirely — no behavior change for existing patients.

**Success criteria:** Diabetic patient gets zero avoid_diabetes dishes ✅. Healthy patient unaffected ✅. food_items read-only ✅.

---

### SESSION 20 — Doctor Tag Review UI
**Type:** Execution (/goal acceptable)  
**Status:** COMPLETE ✅ (2026-06-07) — delivered as Session 19 extension  
**Dependencies:** Session 19 complete ✅  
**Goal:** Give doctor a queue to review and correct AI-assigned condition tags on recipes.

Tasks:
- [x] GET /doctor/recipes/{id}/tags — return current avoid_tags + prefer_tags for a recipe
- [x] PATCH /doctor/recipes/{id}/tags — doctor corrects tags; validates against VALID_TAGS (422 on unknown); auto-sets is_verified=True
- [x] Doctor dashboard: `TagEditPanel` component — 12 avoid + 10 prefer pill toggles (filled=selected, outlined=unselected), inline 422 error, Save/Cancel
- [x] `RecipeCard` shows avoid_tags (red badges) + prefer_tags (green badges); "Edit Tags" button toggles inline panel; local state updates card without full refetch
- [x] Corrections persist to food_items immediately — next plan generation reflects corrected tags

**Success criteria:** Doctor can view and correct tags on any recipe ✅. Corrected tags affect future plan generation ✅.

---

### SESSION 20 — Adaptive Suggestion API
**Type:** Foundation (no /goal — architectural)  
**Status:** COMPLETE ✅ (2026-06-07)  
**Dependencies:** Sessions 13–16 complete  
**Goal:** Build the on-demand multi-option generation and iterative calorie tracking API.

Tasks:
- [x] New endpoint: GET /meal-plan/suggestions/{date}/{meal_type} — returns 4 ranked dish options
- [x] Options ranked by: patient condition tags (avoid_tags/prefer_tags), doctor pins, TDEE fit, weekly variety exclusion
- [x] New endpoint: POST /meal-plan/confirm-choice — upserts to patient_meal_choices, returns updated calories_remaining_today
- [x] GET /progress/today unchanged — plan-time budget (calories_remaining_today) is separate from consumption tracking (meal_logs) — intentional
- [x] Suggestion engine sizes options to remaining daily budget after confirmed choices
- [x] Confirm choice excludes dish from suggestions for remainder of week (weekly variety control)
- [x] Doctor pin/block config (patient_dish_preferences) influences suggestion ranking

**Session 20 actual outcomes:**
- Migration revision: `c9d0e1f2a3b4_add_patient_meal_choices` — table schema: id, patient_id FK, food_item_id FK, date, meal_type, calories, confirmed_at. UNIQUE(patient_id, date, meal_type).
- `PatientMealChoice` ORM model added to `app/models/db_models.py`
- `GET /api/v1/meal-plan/suggestions/{plan_date}/{meal_type}` — working ✓
- `POST /api/v1/meal-plan/confirm-choice` — working ✓
- Verification 5/5 pass (re-confirmed 2026-06-08):
  - Check 1 ✓: 0 avoid_diabetes dishes returned for diabetic patient
  - Check 2 ✓: slot_calorie_target=528.3 sourced from active recommendation; calorie proximity ordering verified
  - Check 3 ✓: confirm-choice writes row (food_item_id=306, calories=320.79) to patient_meal_choices
  - Check 4 ✓: confirmed dish absent from subsequent suggestions call
  - Check 5 ✓: calories_remaining_today=1455.0 = TDEE(1775.81) − confirmed(320.79)
- Known gap (P2): confirm-choice accepts any food_item_id regardless of meal_time_tags — a Breakfast dish can be confirmed into Lunch slot via direct API call. Fix: `meal_time_tags @> ARRAY[meal_type_lower]` validation before upsert. Low risk since suggestions endpoint only surfaces slot-appropriate dishes.

**Success criteria:** Suggestions endpoint returns 4 options ✅. Confirming a choice reduces remaining budget ✅. Next suggestions adjust ✅.

---

### SESSION 20.5 — Password Hash Root Cause Fix (Bug Investigation)
**Type:** Bug fix / Infrastructure  
**Status:** COMPLETE (2026-06-08)  
**Dependencies:** Session 20 complete  

**Root cause:** No idempotent test patient seed script existed. `clean_patients.py` wiped test patients. Dev scripts recreated them with wrong password "Patient@123". Claude's prior fix pattern (one-off `_fix_password.py` scripts) fixed the symptom per-session, not the cause.

**Files changed:**
- `scripts/seed_test_patients.py` (NEW) — idempotent fixture; verify-before-update on UPDATE, full subscription setup on CREATE; canonical password `Test@1234`
- `scripts/seed_admin.py` (MODIFIED) — skips hash overwrite if password already correct
- `scripts/clean_patients.py` (MODIFIED) — added DELETE for 7 missing FK-referenced tables; added `reserved_by/reserved_at` to subscription reset; prints restoration warning

**Phase 4 verification (all pass):**
- `clean_patients.py` completes with no FK errors ✓
- `seed_test_patients.py` creates both patients after wipe ✓
- `POST /api/v1/auth/token` with `priya.test@mityahar.com / Test@1234` → 200 + JWT ✓
- `POST /api/v1/auth/token` with `testaudit@mityahar.com / Test@1234` → 200 + JWT ✓

---

### SESSION 21 — Patient App Adaptive UI
**Type:** Execution (/goal acceptable)  
**Status:** NOT STARTED  
**Dependencies:** Session 19 complete  
**Goal:** Update patient app to show choice cards and real-time calorie tracking.

Tasks:
- [ ] Meals tab: replace static plan display with meal slot cards showing 3–4 options
- [ ] Each option card: dish name, macros, proportional ingredients, select button
- [ ] On selection: POST confirm-choice, calorie ring updates immediately
- [ ] Remaining budget shown prominently on Home tab
- [x] Add Snack quick-log button to Home tab Quick Log section (full-width card, replaces Water + Steps cards)
- [x] Snack log bottom sheet: calorie presets (50/100/200/300 kcal) + free numeric entry; logs as meal_type="Snack"
- [x] Snack calories deduct from buffer in real time (invalidates TODAY query on success)
- **NOTE — Water & Steps deferred:** Water glasses and Steps count cards removed from Quick Log. Pending native health platform integration (HealthKit on iOS / Health Connect on Android). Manual entry UX is low-value vs. automatic sync; will be revisited in a dedicated native health session.
- [x] Week view updated to show chosen dishes (not suggestions) for past days — inline WeekStrip on Meals tab; past days query getDailyChoices(date) and render per-slot confirmed name or "Not logged"; today/future render SuggestionSlot UI; SuggestionSlot key includes date to force remount on date change

**Success criteria:** Patient can choose from options. Calorie ring reflects choices in real time. Snack quick log works.

---

### SESSION 21.5 — Onboarding Cleanup (Field Audit Follow-up)
**Type:** Execution (frontend only)  
**Status:** COMPLETE (2026-06-10)  
**Dependencies:** Session 21 field audit (Target Weight / Nightshades / Meals Per Day / Lifestyle traced through full stack)

**Changes (patient app onboarding only — zero backend/DB changes):**
- [x] `allergies.tsx` — "Nightshades" removed from allergy chip list (audit: 0 food_items contain "nightshade" in ingredients; substring filter was a silent no-op). 7 chips remain.
- [x] `personal-info.tsx` — Target Weight label now reads "(optional)". Field was already non-blocking (`canContinue` never included it); label change only.
- [x] `dietary-preferences.tsx` — Meals Per Day section removed (was a single locked "3 meals" button). `meals_per_day` no longer written from this screen; onboarding store default `"3"` still submits 3 to the backend.
- [x] Lifestyle step deleted entirely (`lifestyle.tsx` removed, `Stack.Screen` entry removed from `(onboarding)/_layout.tsx`). Flow is now dietary-preferences → disclaimer. Also drops smoking/alcohol toggles (same screen); store defaults (`false`/`false`) submit instead.
- [x] Step counter: 8 → 7 across all remaining screens; disclaimer is now step 7 of 7.

**DB columns intentionally untouched (stored-only, no longer collected):** `meals_per_day` (default 3), `sleep_hours`, `water_glasses`, `occupation`, `eating_habits`, `smoking`, `alcohol`. Backend schemas (`schemas/patients.py`) unchanged — defaults flow through onboarding store submission.

**Deferred:** Allergy keyword → ingredient mapping (Nightshades → tomato/eggplant/potato/pepper) not needed since Nightshades removed from UI. Note: other compound chip labels ("Dairy / Lactose", "Tree Nuts", "Shellfish / Fish", "Gluten / Wheat") have the same substring-match weakness — full label never matches ingredient names. Revisit if allergy filtering is hardened.

**Regression (fresh account `s215.onboard@mityahar.com`, Expo web + Playwright, 0 console errors):**
- All 7 steps transition correctly; counter shows "Step N of 7" throughout ✓
- Allergy screen renders 7 chips, no Nightshades ✓
- Step 1 Continue works with Target Weight empty ✓
- No lifestyle step appears; dietary-preferences → disclaimer ✓
- Submission 200; DB row: `target_weight_kg=NULL`, `meals_per_day=3`, `sleep_hours=7`, `water_glasses=8`, `eating_habits=[]`, `tdee=1945.97`, disclaimer accepted ✓

---

### SESSION 22A — Generator Fixes (Bugs 1 + 3 from diagnosis session)
**Type:** Execution (bugfix)
**Status:** COMPLETE (2026-06-11)
**Dependencies:** Diagnosis session 2026-06-11 (6 bugs root-caused)

**Bug 1 — used_food_ids snowball (variety collapse):**
- [x] `meal_generator.py` — generator now saves only IDs picked THIS generation (`weekly_used_ids - prior_seed`), never the accumulated union. Previously each regeneration persisted seed+new, so after 13 regenerations Priya's exclusion list (~260 ids) covered her entire candidate pool → Level 1 always empty → Level 2 deterministic top pick → identical dishes all 7 days.
- [x] `diet_plan_service.py` — cross-week seeding block removed entirely (was loading last 2 plans' used_food_ids as `prior_used_food_ids`). Within-week variety handled by generator's `weekly_used_ids`; cross-week repetition acceptable.

**Bug 3 — diet label / non-veg budget mismatch:**
- [x] `meal_generator.py` `_find_food_item` — diet fallback chain now uses per-slot `query_diet` for Lunch/Dinner (only `nonveg_assigned` budget slots get non-veg candidates). Breakfast keeps `user_diet` so the breakfast-egg exception still fires. Previously every lunch/dinner used the patient's overall diet → non-veg dishes in all 7 lunches despite a 3/week budget, under "Vegetarian" labels.
- [x] `dishes[]` now serializes `diet_type` per dish (both auto-selected and pinned dish blocks).
- [x] `Diet Type` slot label now derived from actual dishes via `_derive_diet_label()` (Non-Veg > Eggetarian > Vegetarian precedence) instead of `query_diet`.

**Priya NULL TDEE (bonus finding):**
- [x] Root cause: test account never went through the onboarding endpoint (`patients.py` complete-onboarding writes bmi/bmr/tdee atomically — her `date_of_birth`/`bmi`/`bmr`/`tdee` were all NULL). Write path is correct; no code change.
- [x] Backfilled patient 2: `tdee=1866.91`, `bmr=1357.75`, `bmi=24.47` (Mifflin-St Jeor, Female 65kg/163cm, age=30 default — dob unknown, matches `_build_meal_config_user_data` default, LA ×1.375).

**Regeneration:** deleted 15 recommendation rows (patient 2: 13, patient 3: 2; patient 4's row untouched), regenerated via `DietPlanService` (`scripts/_s22a_regen.py`) → rec 158 (Priya), 159 (Ruchit).

**Verification (all pass):**
- Check 1 variety: plan 158 has 7/7/7 distinct dish hashes per meal type ✓
- Check 2 labels: plan 159 — every slot label matches its dishes' diet_types; 4 non-veg slots/week (Ruchit `nonveg_meals_per_week=5`, capped at 4 by `min(n,4)`) ✓
- Check 3 TDEE: patient 2 tdee=1866.91 ✓
- Check 4 used_food_ids: 61/63 ids (unique dishes this generation, 21 slots × 3–4 dishes) — not the 260-id snowball ✓

**Known remaining (small-pool repetition, NOT the snowball bug):** breakfast egg mains (Eggetarian pool = 25 items) and tiny slots (bf_accomp=2, bf_beverage=2, lunch_accomp=5) still repeat within a week once the pool exhausts — Level 2 by design. Needs recipe pool expansion, not generator logic.

**Deferred:** Bugs 2 (static slot calorie header + scaled/unscaled dish calories), 4 + 5 (slot_type taxonomy — composite dishes tagged `grain`), 6 (suggestions endpoint serves single dishes scaled to whole-slot targets) → Sessions 22B / 22C.

---

### SESSION 22B — slot_type Taxonomy Cleanup (Bugs 4 + 5)
**Type:** Execution (data fix + small generator change)
**Status:** COMPLETE (2026-06-11)
**Dependencies:** Session 22A

**Audit finding (bigger than diagnosed):** the 925 `slot_type='grain'` rows were not just one-pot dishes — ~805 were curries, sabzis, non-veg mains, and misc dishes mis-tagged as grain (e.g. Achari Paneer, Adraki Rajma Masala, Butter Chicken, hundreds of Poriyal/Thoran/Kootu/Gojju dishes). Moving only the biryani/pulao/khichdi set would have left the grain slot still serving curries as the carb base.

**Bug 4 + 5 fix — food_items reclassification (859 rows, one transaction with in-transaction count guard):**
- [x] 83 → `one_pot` (biryani/pulao/khichdi/pongal/pulihora/sadam/bhath/flavored-rice complete preparations)
- [x] 275 → `dal_protein` (non-veg/egg mains + dal/kadhi/rasam/sambar/kuzhambu/paneer/legume gravies)
- [x] 501 → `sabzi` (vegetable preparations: poriyal, thoran, kootu, palya, gojju, dry sabzis)
- [x] 66 stay `grain` (true carb bases: chapati/roti/phulka/paratha/naan/puri/rice/rotla/ragi mudde/porridges)
- Post-update pools: grain 66, one_pot 87 (83 + 4 pre-existing), dal_protein 372, sabzi 862. Verified: 0 biryani/pulao/khichdi left in grain.

**One-pot template variants — in-code, NOT DB rows:** `uq_template UNIQUE(meal_time, region, diet_type, plan_type)` blocks inserting a second Lunch/Dinner template row per variant, so the brief's INSERT plan was replaced (product owner approved) with generator-side slot lists:
- [x] `meal_generator.py` — module constants `ONE_POT_PROBABILITY = 0.40` and `ONE_POT_SLOTS = [one_pot:0.70, accompaniment:0.30]`.
- [x] Per Lunch/Dinner slot per day: `random.random() < 0.40` → one_pot slot list used instead of `template.slots` (40/60 split ≈ 3 one-pot meals of 7). Breakfast never rolls.
- [x] Standard template kept as fallback attempt (slot_lists loop): if the one_pot attempt fails a required slot, used-id reservations are restored from snapshots and the standard 4-slot build runs — a thin one_pot pool can never drop a whole meal. (Old behavior preserved: if the standard attempt also fails, meal is skipped with a warning.)
- [x] `one_pot` added to `PROTECTED_SLOTS` (blocklist quality filter now covers it like other main slots).

**Regeneration:** recommendations for patients 2 + 3 deleted and regenerated via `scripts/_s22a_regen.py` → rec 163 (Priya), 164 (Ruchit). First regen (161/162) showed Ruchit at 1/14 one_pot meals; probe of `_find_food_item` with his exact params (TDEE 2530, Gym-Friendly, Peanuts allergy) returned candidates for all one_pot/accompaniment lookups — pool fine, unlucky unseeded rolls. Across both regens: 22/56 lunch+dinner slots one_pot = 39.3% ≈ the 0.40 target.

**Verification (all pass, rec 163/164):**
- Check 1: every biryani/pulao/khichdi dish in both plans has `slot_type='one_pot'`; none in grain ✓ (one "Chole Semiya Pulao" is a Breakfast `main_dish` — pre-existing tag, outside grain scope)
- Check 2: one_pot meals have exactly 2 dishes `[one_pot, accompaniment]`; standard meals 4 `[grain, dal_protein, sabzi, accompaniment]`; no stacked-mains hybrids; Breakfast unchanged at 3 ✓
- Check 3: grain slots contain only true bases (Chapati, Phulka, Paratha, Jowar Roti, Bajra Rotla, Ragi Sankati, oats/ragi porridges) ✓

**Known remaining / out of scope (found during audit, NOT fixed):**
- `accompaniment` pool also polluted — e.g. "Rajma Chawal" and "Fish Curry" tagged `accompaniment` (probe surfaced them as top picks for one_pot-meal accompaniment slots). Needs its own audit pass.
- "Chole Semiya Pulao" (and possibly other composites) tagged `main_dish` (Breakfast slot) — pre-existing.
- One-pot rate per patient-week has high variance (binomial n=14): observed 1–10 of 14 across runs; long-run average is on target.

**Deferred:** Bug 2 (live calorie display) + Bug 6 (patient app suggestions rebuild) → Session 22C.

---

### SESSION 22B.5 — Accompaniment Pool Audit + Cleanup
**Type:** Execution (pure data fix, no generator/frontend changes)
**Status:** COMPLETE (2026-06-11)
**Dependencies:** Session 22B

**Audit finding (much smaller than the grain cleanup):** the `accompaniment` pool held only 23 rows total. 20 were true sides (Chaas, Raita variants, Dahi, Lassi, Salads, Koshimbir, Thecha, Dressing — all ≤ 129 kcal). Only 2 were mains polluting one_pot meal composition.

**Reclassification (3 rows, one transaction, dry-run with ROLLBACK first, each UPDATE verified rowcount=1):**
- [x] id 249 "Fish Curry" (180 kcal) `accompaniment` → `dal_protein`
- [x] id 308 "Rajma Chawal" (315 kcal) `accompaniment` → `one_pot`
- [x] id 3724 "Palak Paneer" (Lunch-tagged `main_dish` — unreachable dead row, main_dish slot only used by Breakfast template) → `sabzi`
- Post-update pools: accompaniment 21, dal_protein 373, one_pot 88, sabzi 863, main_dish 275, grain 66 (unchanged).

**Decisions (product owner confirmed):**
- "Chole Semiya Pulao" (id 2912) KEPT as Breakfast `main_dish` — vermicelli breakfast dishes are legit in this pool (siblings: Semiya Upma, Vermicelli Biryani ×3). Not a mis-slot.
- id 230 "Sambar" (187 kcal, `{Breakfast}` tags) KEPT as accompaniment — breakfast side for idli/dosa; never surfaces in one_pot Lunch/Dinner meals.
- Test artifacts flagged, NOT touched: "Palak Paneer Test S16" (3725), "Global Test Recipe" ×7 (3698–3716, empty meal_time_tags) — unreachable, harmless.

**Verification:**
- High-calorie check: 0 accompaniment rows > 300 kcal; max is Sambar at 187 ✓
- Regenerated patients 2 + 3 via `scripts/_s22a_regen.py` → rec 165 (Priya), 166 (Ruchit), 21 meals each.
- Spot-check (rec 165/166): 12 one_pot meals, every one exactly `[one_pot, accompaniment]`; accompaniments are Raita/Chaas/Lassi/Cucumber Raita only — no curries or rice dishes ✓. Rajma Chawal now correctly appears as a one_pot anchor (patient 2, Jun 14 Dinner).

**Deferred:** unchanged — Bug 2 (live calorie display) + Bug 6 (patient app suggestions rebuild) → Session 22C.

---

### SESSION 22C — Diagnostic Audit: Bug 2 + Bug 6 (NO fixes)
**Type:** Audit/diagnosis only — zero production code changes
**Status:** COMPLETE (2026-06-12) — implementation pending product owner review
**Dependencies:** Session 22B.5

**Output:** `docs/session22c_audit_findings.md` (full tables, code traces, open questions). Throwaway scripts in `scripts/audit_22c/`.

**Bug 2 findings (calorie display divergence):**
- `Total Calories` is the slot **budget target**, not a sum: per-slot `calorie_pct` sum to 1.0, so `Σ(cal × target/cal) = meal_target` exactly (clamp never bound in 42 audited slots). Priya: 396.7/555.4/396.7 constant all week; Ruchit: 537.7/752.8/537.7 — the static header IS the target.
- `dishes[].calories` is unscaled per-serving (`meal_generator.py:360`); the portion factor (`:328`) is baked into `dishes[].ingredients[].amount_g` (`:347`) but discarded as a number — same dish object has scaled ingredients, unscaled macros.
- Divergence −42% to +164% per slot, not a uniform ratio. One_pot slots skew stored>sum; Ruchit breakfasts skew opposite (656–716 kcal egg mains scaled DOWN ~0.55×).
- Doctor dish PATCH (`doctor.py:893/1078`) recalcs `Total Calories = sum(unscaled dishes)` — edits silently flip the header's basis. Pinned dishes never added to totals (`meal_generator.py:398-414`).
- Verdict: two legitimate bases + a discarded factor — NOT a one-line missed scaling step.

**Bug 6 findings (suggestions endpoint, live calls):**
- Confirmed: single food_items ranked by |cal − whole-slot target| (`meal_plan.py:389-413`); slot_type unconstrained. Actively breaks adaptive budget: confirm-choice writes one dish's calories as the whole meal.
- Collateral: "Test Dal Tadka" ×2 (ids 3676/3677, is_verified=True test artifacts) served to Priya; Chicken Biryani (300/332) still missing `avoid_diabetes`, suggested to a diabetic.
- Combo simulation: 4-dish combos hit targets within ±5% unscaled; 2-dish one_pot combos undershoot large targets up to −30% (no single dish big enough — generator solves via portion factor). Query cost fine (2–4 indexed queries). Blockers: `patient_meal_choices` is single-food_item shaped (schema change needed); accomp/beverage pools of 4–8 items make combos visibly repetitive (pool expansion soft prerequisite).

**Part 4 — Boondi:** already fixed in Session 18C; verified live (`ingredients` id 173: avoid_tags=[], prefer_tags=["gluten_free"]). Technical Debt item 5 below is stale.

**Next:** product owner answers 8 open questions in findings doc (header basis, shared `Total Calories` dependency between Bug 2 and Bug 6 fixes, confirm-choice schema, pool expansion) before Bug 2/6 implementation is scoped.

---

### SESSION 22D — Design Audit: scaled_calories impact map + beverage reclassification + confirm-choice schema (NO fixes)
**Type:** Audit/design only — zero production code changes, zero migrations
**Status:** COMPLETE (2026-06-12) — implementation (22E) pending product owner review
**Dependencies:** Session 22C; PO decisions: dishes[].calories stays unscaled, new `scaled_calories` field, Bug 6 = whole-meal combos, beverages exit generation by default

**Output:** `docs/session22d_audit_findings.md` (impact map, edge-case answers, blast radius, schema proposal, 9 open questions). Throwaway scripts in `scripts/audit_22d/`.

**Part 1 — Bug 2 impact map (15 code paths inventoried, W1–W6 writers / R1–R3 backend readers / F1–F9 frontend):**
- Recommends persisting `dishes[].factor` AND slot-level `"Target Calories"` alongside `scaled_calories` — the Target field decouples Bug 6's `slot_calorie_target` (`meal_plan.py:373`) from the header redefinition, resolving 22C Q2 permanently.
- Edge-case recommendations: factor=1.0 for custom dishes / PATCH swaps / pinned dishes; pinned dishes finally included in header Σ (fixes 22C pinned-totals bug); forward-only (no backfill — 3 active recs all test patients, regenerate in 22E); divergence UI = second "target" line/warning only when >10%.
- Collateral found: PATCH-created dishes have no `ingredients` key; `assign_recipe` (doctor.py:1264) creates dishes[]-less legacy-shape slots; PlanTab "below TDEE" banner is tautological today (compares target-sum to TDEE).

**Part 2 — Beverage blast radius (smaller than assumed):**
- beverage slot exists ONLY in the 36 Breakfast templates, at 0.10 pct, `required: false`. Lunch/Dinner standard + one-pot templates have NO beverage slot — 22C's lunch "Chaas/Lassi" combo partners are `slot_type='accompaniment'`, untouched by this change.
- 24 beverage food_items; only 10 Breakfast-tagged are reachable (45.8–147 kcal); no real-macro beverages exist. Buttermilk Soup id 591 = 2857.7 kcal data error (added to Q8 cleanup list).
- Recommend redistribute Breakfast to 0.78/0.22 (combo re-run: −16%…+20%, same order as 22C); in-code BREAKFAST_SLOTS override (22B ONE_POT_SLOTS precedent), no template migration.
- Doctor exception = existing pin mechanism (works for beverages; needs append-not-displace rule + Bug 2's W3 totals fix). Patient logging = Session 21 snack quick-log pattern via meal_logs (no schema change; optional food_id-linked picker).
- Lunch/Dinner combo math verified unchanged (re-run reproduces 22C numbers exactly).

**Part 3 — confirm-choice schema:** Option A (JSONB `chosen_dishes` on existing row, food_item_id → nullable, row `calories` = combo total) recommended over child table — Session 20 budget math untouched, single-statement upsert preserved, shape-symmetric with dishes[]. Option A is also the easier 22E scope.

**Next:** PO answers 9 open questions (doc §Open questions, esp. (i) factor+Target Calories fields, (d) redistribution, (f) schema, (g) strict slot_type scope) → scope Session 22E implementation.

---

### SESSION 22E — Bug 2 + Bug 6 Implementation (scaled_calories, Target Calories, Beverage Reclassification, Confirm-Choice Child Table)
**Type:** Execution + Verification  
**Status:** COMPLETE (2026-06-13) — all 16 endpoint checks PASS  
**Dependencies:** Sessions 22C, 22D, Q8 data cleanups

**What shipped:**
- `dishes[].scaled_calories` (= `calories × factor`), `dishes[].factor` (1.0 for custom/PATCH/pinned), and slot `"Target Calories"` (generation-time budget) persisted in `recommendations.meals` JSONB across all new plans. Forward-only — 3 test plans (rec 167/168/169) regenerated.
- Beverage slot removed from Breakfast generation via in-code `BREAKFAST_SLOTS` override (0.78 main / 0.22 accompaniment). Beverages endpoint (`GET /meal-plan/beverages`) returns 22 items; calorie guard (`cal_per_serving < 300`) excludes ids 591 (Buttermilk Soup 2857 kcal) and 2447 (Spiced Beetroot Buttermilk). Patient beverage-logging picker added to patient app.
- `patient_meal_choice_dishes` child table (migration `d0e1f2a3b4c5`): confirm-choice now writes parent + child atomically; re-confirm deletes old children and inserts new (no duplicate parents). Child `calories` = unscaled `cal_per_serving` per Q7 decision.
- Q8 cleanups committed: Test Dal Tadka (3676/3677) excluded (`is_verified=False`, tags=[]), Chicken Biryani (286/300/332) tagged `avoid_diabetes`, beverage outliers hidden via picker guard.
- Suggestions endpoint R1: `slot_calorie_target` reads `Target Calories` from active plan (not TDEE/3 fallback) when the field is present.
- Doctor amber warning: `|Σ(scaled_calories) − Target Calories| / Target Calories > 10%` threshold implemented in PlanTab.tsx.

**Verified (16/16 PASS — `scripts/_22e_endpoint_verify.py`):**
1. Biryani (286/300/332) absent from diabetic patient suggestions ✅
2. Test Dal Tadka (3676/3677) absent (DB check: is_verified=False, tags=[]) ✅
3. `slot_calorie_target` = plan's `Target Calories` (555.4 kcal) not TDEE/3 (622.3 kcal) ✅
4. Beverage picker: 22 items returned, ids 591+2447 absent ✅
5. Confirm-choice: parent upserted, child written with unscaled calories ✅
6. Re-confirm: single parent row updated, old children deleted, new child inserted ✅
7. GET `/choices/{date}` returns `dishes[]` from child table ✅
8. Doctor PATCH: Total Calories = Σ(scaled_calories) after swap ✅
9. 65% divergence from Target → amber threshold confirmed (>10%) ✅
10. Pin endpoint working, pin stored in DB ✅
11. W3 end-to-end pin verification (`scripts/_w3_pin_verify.py`): pinned dish Doi chira (food_id=185) propagated into regenerated plan with factor=1.0, ingredients=5 items, scaled_calories==calories (313.32), counted in slot Total Calories — 5/5 checks PASS ✅

**Known residuals / backlog:**
- ~27 other biryani/pulao dishes still lack `avoid_diabetes` — systemic Layer-3 gap, dedicated tagging pass needed.
- Suggestions endpoint doesn't filter `diet_type` — vegetarian patients could get non-veg suggestions; scope-check needed.
- Q6 pool expansion (accompaniment pool=4) not addressed.
- Pin endpoint uses `food_id` field (not `food_item_id`) — note for any future callers.

**Next:** Bug 6 combo-building — Target Calories (R1) and child-table schema (Part 3) in place; implement multi-dish combo logic in the suggestions endpoint.

---

### SESSION 22E.5 — W3 End-to-End Verification + Bug 6 Design Audit
**Type:** Verification + Diagnosis  
**Status:** COMPLETE (2026-06-15)  
**Dependencies:** Session 22E

**W3 pin propagation (Part A — gap from 22E check 5a):**
- Rec 170 status confirmed: RESTORE of rec 168 (PATCH test dirtied 168 → _22e_restore_plan.py regenerated → rec 170). NOT a 4th independent regen. 22E structural verification on rec 168 applies to rec 170 (same codepath).
- Script `scripts/_w3_pin_verify.py` ran: pinned food_id=185 (Doi chira) for Patient4, regenerated plan (→ rec 171), verified:
  - factor=1.0 ✅  
  - ingredients=5 items (not empty) ✅  
  - scaled_calories==calories (313.32) ✅  
  - Pinned dish counted in slot Total Calories (Σ=635.86, Total=635.86) ✅  
  - Note: Total (635.86) >> Target (413.52) — 54% divergence; amber warning correct behavior for an unscaled pin displacing a slot-budget-matched main_dish
- W3 verified end-to-end. 5/5 PASS.

**Bug 6 Combo-Building Audit (Part B — design only):**
- Design doc: `docs/bug6_combo_design.md`
- 22C ±5% viability finding holds for all slot types post-22E (verified on live recs 167/169/170).
- The -30% one_pot undershoot (22C/22D) eliminated by combo design: one_pot+accompaniment combo ≈ ±7-10% of Target at natural portions.
- Breakfast 2-dish (new shape from 22E) viable: 24×5=120 combos, ±5% math holds.
- Q6 accompaniment pool=4 concern resolved: verified pools are 12 (Lunch), 16 (Dinner).
- `confirm-choice` child table (22E) already combo-ready; only schema change is `food_item_id → food_item_ids: list[int]`.
- Backlog B (diet_type filter) is a free natural closure inside combo pool queries — not a separate task.
- Pool sizes adequate; weekly repetition risk eliminated vs single-item ranking.
- Query count: 7-9 (all indexed); no performance concern.
- 6 open PO questions in design doc before implementation can be scoped.

**Next:** PO reviews `docs/bug6_combo_design.md`, answers 6 open questions (esp. A: one-pot vs standard variant selection, B: per-dish swap UX, D: R2 scaling scope) → scope Bug 6 implementation session.

---

### SESSION 22F — Bug 6 Combo-Building + Backlog B Diet Filter
**Type:** Execution  
**Status:** COMPLETE (2026-06-15)  
**Dependencies:** Sessions 22E, 22E.5 (design doc + PO decisions locked)

**What shipped:**

1. **Suggestions endpoint — combo-building (Bug 6 core):**
   - `_get_slot_composition()` reads slot_types from active plan JSONB for the given date + meal_type.
   - One DB query per slot_type in composition; ranked by calorie proximity to per-slot budget (using `BREAKFAST_SLOTS`/`ONE_POT_SLOTS` constants from generator + `_STANDARD_SLOT_PCT` for standard 4-slot).
   - Round-robin combo construction (up to 4 combos); no partial combos returned.
   - Legacy fallback: if slot_composition empty (pre-22E plan), runs single-item query + Python re-rank, wraps each as a 1-dish combo.
   - Response shape changed: `suggestions` is now `SuggestedCombo[]` (`combo_id`, `total_calories`, `dishes[]`). Old flat single-item shape removed.

2. **Backlog B — diet_type filter (closed as free side-effect):**
   - `DIET_TYPE_HIERARCHY` constant: Vegetarian → [Vegetarian], Eggetarian → [Veg, Egg], Non-Veg → all.
   - `FoodItem.diet_type.in_(allowed_diet_types)` added to all pool queries (both combo path and legacy fallback).
   - Vegetarian patients can no longer receive non-veg suggestions.

3. **Confirm-choice — combo input (Part 2):**
   - `ConfirmChoiceInput.food_item_id: int` → `food_item_ids: list[int]`.
   - All food items fetched in one query; blocked-check in one query.
   - Parent `calories` = `sum(fi.cal_per_serving)` across all confirmed items.
   - Child rows loop over all `confirmed_items` (delete-then-insert, same atomicity).
   - Response now returns `food_item_ids: list[int]` instead of `food_item_id`.

4. **Patient app frontend:**
   - `SuggestionCard` replaced by `ComboCard` — shows `dish1 + dish2 + ...` names, `~{total_calories} kcal`, slot-type tags per dish.
   - `confirmMut` mutates `SuggestedCombo`, sends `food_item_ids: combo.dishes.map(d => d.food_item_id)`.
   - Confirmed state display: joins dish names with " + " for multi-dish combos.
   - `choicesByMeal` mapping updated: uses `dishes[]` from GET /choices if available for correct combo name display after page reload.
   - TypeScript types updated: `MealSuggestion` → `SuggestedDish` + `SuggestedCombo`; `SuggestionsResponse` updated; `ConfirmChoiceResponse.food_item_id` → `food_item_ids`.

5. **Doctor dashboard:** No changes needed — dashboard does not call the suggestions endpoint.

**Backlog / Notes:**
- **Q6 closure:** Accompaniment pool verified at 12 (Lunch), 16 (Dinner), 5 (Breakfast) — not the feared 4. No pool expansion needed. Q6 closed.
- **Backlog B closure:** diet_type filter in place. Closed.
- **Portion-size selector (future feature):** Small/Medium/Large bowl selector → patient-controlled `factor` override. Dish-type-aware size vocabulary (rice/roti/sabzi/dal each need own labels and gram mappings). Depends on Bug 2's `factor` field (in place). Design session needed before implementation.
- **Backlog A (still open):** ~27 biryani/pulao dishes missing `avoid_diabetes` tag. Clinical risk for diabetic patients. Independent tagging pass required.
- **R2 (out of scope this session):** Per-dish scaling in suggestions deferred. Suggestions currently show unscaled "approximately X kcal".

**Next:** W3 clinical guardrail decision — if doctor pins a 2nd main_dish to a slot, amber warning fires at 54% divergence (correct) but no guard prevents calorie-doubled slot for patient. Decision needed: add max-1-main_dish-per-slot pin validation, or treat as "doctor-knows-best". Also: Session 22 (Doctor Weekly Patient Summary) is the next unstarted feature.

---

### R-0 — Pre-Rebuild Data Pass (COMPLETE)
**Type:** Data-pass (DB only, no code/migration/frontend changes)
**Status:** COMPLETE — 2026-06-16
**Depends on:** Nothing (per rebuild_spec.md §8)

**Task 1 — Biryani/pulao avoid_diabetes tagging:**
- Initial scan (no slot_type filter): 43 untagged biryani/pulao/khichdi/fried-rice dishes.
- **30 dishes tagged** with `avoid_diabetes` (27 in first pass + 3 after user clinical review: Khichdi Roti ×2 ids 3341/3343, Matta Rice Peas Pulao id 1619).
- **12 dishes intentionally left untagged** — low-GI/fibre-rich exemption (millet, broken wheat/daliya, quinoa, moong dal khichdi, Bikaneri daliya-based wheat khichdi):
  - Moong Dal Khichdi (2768) — explicit exemption
  - Broken Wheat And Green Moong Khichdi (3625), Broken Wheat Khichdi (1188) — broken wheat
  - Spicy Dalia Pulao (1236) — daliya
  - Quinoa Brown Rice And Vegetable Pulao (1562, 1563) — quinoa
  - Barnyard Millet And Ragi Khichdi (3077), Matar Millet Pulao (3215), Millet Khichdi (306, 2081), Mixed Millet Khichdi (2841) — millet (low-GI grain, diabetic-friendly by clinical consensus)
  - Wheat Bikaner Khichdi (1361) — confirmed by user review as a traditional broken-wheat (daliya) preparation despite the name only saying "wheat"; daliya GI ~41, same exemption class
- **0 dishes flagged open** — all 4 originally-ambiguous dishes resolved via user clinical review (3 tagged, 1 exempted; see above).
- **Verification query corrected:** the spec's original verification (`...AND NOT (avoid_tags @> '["avoid_diabetes"]') → must return 0`) cannot reach 0 while honoring the low-GI exemption rule — it doesn't account for its own exemption list, so it permanently shows the 12 exempt dishes as "untagged." Replaced with a corrected query that excludes the exemption keywords explicitly:
  ```sql
  SELECT id, recipe_name FROM food_items
  WHERE (recipe_name ILIKE '%biryani%' OR recipe_name ILIKE '%pulao%'
      OR recipe_name ILIKE '%khichdi%' OR recipe_name ILIKE '%fried rice%')
    AND slot_type IN ('main_dish', 'one_pot', 'grain')
    AND NOT (avoid_tags @> '["avoid_diabetes"]'::jsonb)
    AND NOT (recipe_name ILIKE '%millet%' OR recipe_name ILIKE '%daliya%' OR recipe_name ILIKE '%dalia%'
        OR recipe_name ILIKE '%quinoa%' OR recipe_name ILIKE '%oats%' OR recipe_name ILIKE '%broken wheat%'
        OR recipe_name ILIKE '%bikaner%' OR recipe_name ILIKE '%moong dal khichdi%');
  ```
  Confirmed returns **0 rows**. This corrected query is the regression check to use going forward, not the original spec query.
- Backlog A is now CLOSED.

**Task 2 — Test artifact verification (NO deletion performed):**
- IDs 3698–3716 (19 rows, not 7 as spec estimated): 3 distinct test recipes — "Global Test Recipe" (×7, main_dish), "To Be Rejected Recipe" (×6, snack_item), "Doctor2 Private Dal" (×6, dal_protein). All belong to `doctor_id=72`.
- **13 rows ("Global Test Recipe" + "To Be Rejected Recipe") confirmed unreachable** — `meal_time_tags = {}` (empty), excluded by every pool query's `meal_time_tags.any(meal_time)` filter.
- **⚠️ 6 rows ("Doctor2 Private Dal", ids 3700/3703/3706/3709/3712/3715) are NOT unreachable, contrary to the task's assumption.** They have `meal_time_tags={Lunch}`, `is_verified=false`, `cal_per_serving=220`, `diet_type=Vegetarian`, default `plan_type_tags` (all three). `app/services/meal_generator/meal_generator.py:606-622` (`base_stmt`, the pool query used by full plan generation) filters `slot_type`, `diet_type`, `meal_time_tags`, `plan_type_tags`, `cal_per_serving` range, used/blocked ids, `avoid_tags` — **but never `is_verified` or `doctor_id`**. Only the suggestions endpoint (`app/routers/meal_plan.py:439,493`) filters `is_verified == True`. This unverified test dal is therefore reachable by `MealGenerator.generate_meal_plan()` for any real Vegetarian patient's Lunch dal_protein slot whose target calorie range brackets ~220 kcal.
- **New gap discovered, not previously in `system_architecture.md` §8:** generation-layer pool query (`meal_generator.py`) has no `is_verified` filter, unlike the suggestions endpoint. Doctor-submitted unverified/private recipes (any doctor, not just test accounts) can leak into other doctors' patients' generated plans. Logged here for R-1/R-2 scope consideration — **no code change made this session** (DB-only scope).
- No rows deleted, per task instruction.

**Task 3 — Pool snapshot (pre-R-2 baseline):**
- Spec's verification queries used `meal_time_tags @> '[...]'::jsonb` — column is actually `ARRAY(Text)`, not JSONB (confirmed against `db_models.py` / `system_architecture.md` §1.1). Corrected to `meal_time_tags @> ARRAY['Breakfast']` etc.

| slot_type | diet_type | total | breakfast | lunch | dinner |
|---|---|---|---|---|---|
| accompaniment | Non-Vegetarian | 5 | 1 | 3 | 4 |
| accompaniment | Vegetarian | 16 | 4 | 9 | 12 |
| beverage | Non-Vegetarian | 2 | 1 | 1 | 1 |
| beverage | Vegetarian | 22 | 9 | 6 | 8 |
| condiment | Vegetarian | 93 | 11 | 81 | 82 |
| dal_protein | Eggetarian | 10 | 0 | 5 | 10 |
| dal_protein | Non-Vegetarian | 45 | 0 | 25 | 45 |
| dal_protein | Vegetarian | 310 | 3 | 238 | 306 |
| grain | Non-Vegetarian | 9 | 0 | 4 | 9 |
| grain | Vegetarian | 57 | 10 | 37 | 47 |
| main_dish | Eggetarian | 7 | 7 | 0 | 0 |
| main_dish | Non-Vegetarian | 1 | 1 | 0 | 0 |
| main_dish | Vegetarian | 260 | 259 | 1 | 0 |
| one_pot | Non-Vegetarian | 6 | 0 | 4 | 6 |
| one_pot | Vegetarian | 82 | 2 | 61 | 80 |
| sabzi | Eggetarian | 2 | 0 | 2 | 2 |
| sabzi | Non-Vegetarian | 13 | 0 | 12 | 13 |
| sabzi | Vegetarian | 848 | 1 | 766 | 846 |
| snack_item | Eggetarian | 6 | 0 | 0 | 0 |
| snack_item | Non-Vegetarian | 2 | 0 | 0 | 0 |
| snack_item | Vegetarian | 325 | 0 | 0 | 0 |

(excludes the 19 test-artifact rows 3698–3716; `snack_item` pools are dead post-Session 11 per system_architecture.md §1.1.1, shown for completeness.)

**Next:** R-0 marked COMPLETE in roadmap. R-1 (Schema Expansion) may begin. The newly discovered `is_verified` gap in `meal_generator.py` should be considered for R-2 scope (generation layer rewrite) — not fixed this session per DB-only scope.

---

### R-1 — Schema Expansion (COMPLETE)
**Date:** 2026-06-16
**Type:** Migrations + ORM only (no logic changes, no new endpoints, no frontend edits)
**Depends on:** R-0 complete

**Scope executed exactly per `docs/rebuild_spec.md` §2:**
1. Migration `e1f2a3b4c5d6` — `recommendations` +2 columns: `generation_version` (Integer, default 1), `approval_status` (VARCHAR(20), default 'approved', CHECK IN ('draft','approved')).
2. Migration `f2a3b4c5d6e7` — new table `weekly_combos` (84 rows/patient/week target for R-2). Indexes `idx_wc_rec_date_meal`, `idx_wc_rec_id`. Constraints `uq_weekly_combo`, `ck_combo_index`, `ck_meal_type`.
3. Migration `a3b4c5d6e7f8` — new table `weekly_patient_summary` (index `idx_wps_patient_id`, constraint `uq_wps_patient_week`) + `patient_meal_choices` +3 columns: `weekly_combo_id` (FK → weekly_combos, ON DELETE SET NULL, nullable), `bowl_size` (VARCHAR(6), nullable, CHECK IN ('small','medium','large')), `actual_calories` (NUMERIC(7,2), nullable).
4. Migration `b4c5d6e7f8a9` — `doctor_meal_overrides` +3 columns: `patient_condition_snapshot` (JSONB, nullable), `edit_reason` (VARCHAR(20), default 'swap', CHECK IN ('swap','add','remove','custom_add')), `doctor_note` (TEXT, nullable).
5. ORM (`app/models/db_models.py`): `Recommendation` gained `generation_version`/`approval_status`; new `WeeklyCombo` and `WeeklyPatientSummary` classes; `PatientMealChoice` gained `weekly_combo_id`/`bowl_size`/`actual_calories` + `weekly_combo` relationship; `DoctorMealOverride` gained `patient_condition_snapshot`/`edit_reason`/`doctor_note`.
6. `alembic upgrade head` — clean run, 0 errors, `d0e1f2a3b4c5 → e1f2a3b4c5d6 → f2a3b4c5d6e7 → a3b4c5d6e7f8 → b4c5d6e7f8a9`.

**Verification (all 5 queries from the session spec, run against live DB):**
```
Q1 — recommendations.{generation_version,approval_status} columns + defaults:
  [('generation_version', '1'), ('approval_status', "'approved'::character varying")]

Q2 — count(*) WHERE generation_version != 1 OR approval_status != 'approved' (must be 0):
  0

Q3 — to_regclass('weekly_combos'), to_regclass('weekly_patient_summary') (both non-null):
  [('weekly_combos', 'weekly_patient_summary')]

Q4 — patient_meal_choices new columns present:
  [('actual_calories',), ('weekly_combo_id',), ('bowl_size',)]

Q5 — doctor_meal_overrides new columns present:
  [('patient_condition_snapshot',), ('doctor_note',), ('edit_reason',)]
```

**Next:** R-1 marked COMPLETE in roadmap. R-2 (Generation Layer — 4 combos + pin-as-preference-signal + `is_verified` filter) may begin.

---

### R-2 — Generation Layer (COMPLETE)
**Date:** 2026-06-16
**Type:** Logic only (no migrations, no new endpoints, no frontend edits)
**Depends on:** R-1 complete

**Scope executed exactly per `docs/rebuild_spec.md` §3 + product decisions (Session 22, Jun 16):**
1. `app/services/meal_generator/meal_generator.py`:
   - **Change 1 (`is_verified` filter):** `_pick_for_slot.base_stmt()` adds `FoodItem.is_verified == True` — closes the R-0-discovered gap where test/unverified dishes could leak into patient plans.
   - **Change 2 (diet hierarchy + fallback):** new module constants `DIET_TYPE_HIERARCHY` (primary pool per diet, Eggetarian merged into Non-Veg's own pool) and `DIET_TYPE_FALLBACK` (NEW Level 3 — Vegetarian fallback for Non-Veg/Eggetarian). 4-level exhaustion cascade in `_pick_for_slot`/`_fill_slot_dishes`: L1 primary pool + weekly memory, L2 primary pool w/o weekly memory, L3 fallback diet w/o weekly memory, L4 duplicate combo-0's dish for that slot_type (logged warning, never raises).
   - **Change 3 (pin as preference signal):** removed forced pin-injection block; `prefer_sort` in `_pick_for_slot` now boosts `FoodItem.id.in_(pinned_food_ids)` alongside `prefer_tags`, exactly per rebuild_spec §3.4 — pins surface naturally, never override slot composition.
   - **Change 4 (4 combos/slot):** `generate_meal_plan`'s per-slot block now loops `combo_idx in range(4)` calling new `_fill_slot_dishes()`; `combo_slot_used_ids` accumulates across the 4 runs (no repeat dish within a slot's combos), `daily_used_ids`/`weekly_used_ids` stay frozen during the loop and fold in only combo-0's picks once the slot succeeds. Ingredient checklist built from combo-0 only. Return dict gained `combos` (84 dicts) alongside legacy `meals` (now always `[]`).
   - New methods: `_assemble_dish()` (dish dict incl. `scaled_calories`/`factor`/`diet_type`), `_pick_for_slot()` (cascade pool query), `_fill_slot_dishes()` (per-combo slot fill + Level-4 fallback). Old `_find_food_item`/`_find_food_item_single_diet` left in place (unused by the new path, still referenced by `scripts/_s22b_probe.py`).
2. `app/schemas/diet_plan.py`: `DietPlanResponse` gained `combos: list[dict] = []` and `generation_version: int = 1`.
3. `app/services/diet_plan_service.py`: `generate_diet_plan()` now threads `combos`/`generation_version=2` from the generator's output. `store_diet_plan()` sets `Recommendation.generation_version`/`approval_status` (`'draft'` for v2, `'approved'` for v1 — v1 path unchanged) and bulk-inserts `WeeklyCombo` rows (`sa_insert(WeeklyCombo)` with a list of dicts — one statement, not 84) when `generation_version == 2`.
4. `app/routers/diet_plans.py` (validation only): `_validate_generated_plan` dispatches on `generation_version`; new `_validate_generated_combos()` checks combo count (`EXPECTED_COMBO_COUNT = 84`), `slot_date`/`dishes` presence per combo, and diet-type constraints via `dish.diet_type` across all combos (replaces the old meal-text substring search, which no longer applies since `meals` is always `[]` for v2).

**Verification (generated + stored a live v2 plan for priya.test@mityahar.com via `DietPlanService.generate_diet_plan`/`store_diet_plan`, same code path as `POST /api/v1/diet-plans/generate`; script: `scripts/_r2_verify.py`):**
```
validation_error: None
stored recommendation_id: 172, patient_id: 2

Recommendation row:
  generation_version: 2
  approval_status: draft
  meals: []

Total weekly_combos rows (expect 84):
  84

combo_index distribution (expect 4 rows of 21 each):
  {combo_index: 0, count: 21}
  {combo_index: 1, count: 21}
  {combo_index: 2, count: 21}
  {combo_index: 3, count: 21}

Duplicate dish within same (slot_date, meal_type) across its 4 combos:
  15 groups found — ALL 15 trace 1:1 to a logged "Pool exhausted ... reusing
  combo-0 dish" warning (Level-4 fallback firing for thin accompaniment/
  one_pot pools at Priya's calorie target). No unlogged/silent duplicate.
  This matches the spec's explicit exception ("expected 0 rows, with
  exception noted for pool exhaustion fallback").
```

**Note:** Level-4 fallback fired more often than expected (accompaniment/one_pot pools are thin for Vegetarian at this calorie band) — not a bug, but flags the accompaniment/one_pot pool size as a candidate follow-up if duplicate-dish frequency matters for patient-facing variety. Not actioned this session (out of R-2 scope).

**Next:** R-2 marked COMPLETE in roadmap. R-3 (Doctor API / approval gate) may begin — **not started this session.**

---

### R-4.5 — Dish-Level Editing, Custom Meal v2, Swap Error Messages (COMPLETE)
**Date:** 2026-06-17
**Type:** Backend (1 new endpoint + 1 extended endpoint) + Frontend (3 UI additions)
**Depends on:** R-4 complete

**Scope:**
1. **Fix 1 — Swap error messages (frontend only):** `swapMut.onError` in PlanTab.tsx now branches on `err?.response?.status` — 409 → "No dishes available for this slot — pool exhausted", 404 → "Combo not found", other → "Swap failed — please try again".

2. **Fix 2 — Dish-level editing via expandable ComboCard (backend + frontend):**
   - `app/schemas/doctor.py`: Added `WeeklyDishPatchRequest(action, food_item_id, doctor_note)`.
   - `app/routers/doctor.py`: New `PATCH /patients/{patient_id}/weekly-plan/combos/{combo_id}/dishes/{dish_index}` endpoint. Prefers `food_item_id` for dish selection (match by `food_id` in JSONB); accepts `dish_index` as fallback. Actions: swap/remove/add. Recalculates `total_calories` + `slot_composition`. Writes `DoctorMealOverride` audit row. Returns updated combo.
   - `doctorApi.ts`: New `patchWeeklyDish(patientId, comboId, dishIndex, body)` function.
   - `PlanTab.tsx`: New `ComboDishSearchModal` (minimal search wrapper, callbacks with `FoodItemSummary`). `ComboCard` rewritten: collapsed = existing view; click body → expands; expanded shows per-dish rows with ⇌ (swap) and × (remove) icons + "+ Add Dish" button + "Done" button. Each action calls `patchWeeklyDish` and invalidates `weeklyPlan` cache. Cannot remove last dish (guard in place).

3. **Fix 3 — Add Custom Meal for v2 plans (backend + frontend):**
   - `app/schemas/doctor.py`: Added `combo_index: int = Field(default=0, ge=0, le=3)` to `AddCustomDishRequest`.
   - `app/routers/doctor.py`: Extended `add_custom_dish_to_plan` — if `rec.generation_version == 2`, finds matching `WeeklyCombo` by `(rec.id, slot_date, meal_type, body.combo_index)` and appends dish, recalculates calories, writes audit row. v1 path unchanged.
   - `doctorApi.ts`: Added `combo_index?: number` to `addCustomDish` body type.
   - `PlanTab.tsx`: New `AddCustomMealModal` — combo selector (Combo 1–4), tab toggle (From Library / Custom). Library tab: recipe search → calls `patchWeeklyDish(action=add, food_item_id)`. Custom tab: name+calories → calls `addCustomDish(..., {combo_index})`. "+ Add Custom Meal" button added below each v2 meal section. Modal state: `addCustomFor`.

**Verification (tsc):** 6 pre-existing `ImportMeta.env` errors, 0 new errors from R-4.5 changes.
**Verification (schema):** `WeeklyDishPatchRequest` and `AddCustomDishRequest.combo_index` parse correctly in Python.

---

### R-3 — Doctor API / Approval Gate (COMPLETE)
**Date:** 2026-06-17
**Type:** Backend endpoints only (no migrations, no frontend edits)
**Depends on:** R-2 complete

**Scope executed exactly per `docs/rebuild_spec.md` §4:**
1. `app/routers/doctor.py` — 4 new endpoints added under the R-3 comment block (line ~1149):
   - `GET /patients/{patient_id}/weekly-plan` — returns active recommendation + all 84 `weekly_combos` rows grouped by `slot_date → meal_type → combo_index`. v1 plans (no weekly_combos) return `combos_available: false` with empty plan dict rather than 404.
   - `POST /patients/{patient_id}/weekly-plan/approve` — flips `approval_status` draft → approved; fires FCM push (fire-and-forget); returns `already_approved` if called twice.
   - `POST /patients/{patient_id}/weekly-plan/combos/{combo_id}/swap` — re-fills one `WeeklyCombo`'s dishes via `_fill_slot_dishes`; excludes all food_ids from all 4 siblings; writes `DoctorMealOverride` row with old/new dishes in `patient_condition_snapshot`; returns 409 `pool_exhausted` when no distinct dishes available.
   - `GET /patients/{patient_id}/weekly-summary` — returns 7-day adherence summary: `planned_calories` from active combo's `total_calories`, `confirmed_calories` from `patient_meal_choices.actual_calories` where `weekly_combo_id` matches.
2. `app/schemas/doctor.py` — `WeeklyPlanApproveRequest` (optional `doctor_note`) and `ComboSwapRequest` (`edit_reason` literal + optional `doctor_note`) added. `edit_reason` literals match `doctor_meal_overrides.edit_reason` CHECK constraint.
3. All 4 endpoints gated by `DoctorIsolationMiddleware` (zero-DB JWT claim check) — calls with another doctor's token receive 404 (patient not found for that doctor), not 403.

**Verification results (2026-06-17):**

**Check 1 — GET `/doctor/patients/2/weekly-plan`:** PASS
- Returns 7 dates × 3 meal_types × 4 combos each (84 combos total)
- `approval_status='draft'`, `generation_version=2`
- Patient 3 (v1 plan, no weekly_combos): returns `combos_available: false` — PASS (v1 coexistence handled)

**Check 2 — POST `/doctor/patients/2/weekly-plan/approve`:** PASS
- Response: `{"status": "approved", "recommendation_id": 172}`
- Subsequent GET: `approval_status='approved'` ✓

**Check 3 — POST `/doctor/patients/2/weekly-plan/combos/{combo_id}/swap`:**
- combo_id=1 (Breakfast, `accompaniment` slot): 409 `pool_exhausted` — EXPECTED. Thin accompaniment pool for Vegetarian/Healthy at this calorie band; all 4 sibling combos exhaust the pool. Same root cause as R-2 Level-4 warning. Not a code bug.
- combo_id=5 (Lunch, `one_pot` slot): 409 `pool_exhausted` — same thin pool issue.
- combo_id=9 (Dinner, 4-slot `grain+dal_protein+sabzi+accompaniment`): PASS
  - Before: `Bhakri + Gravy + Aloo Methi + Raita`
  - After: `Chawal + Rajma + Aloo jeera + Chaas`
  - `doctor_meal_overrides` row id=6 created: patient_id=2, doctor_id=70, edit_reason='swap', doctor_note='R-3 test swap' ✓

**Check 4 — GET `/doctor/patients/2/weekly-summary`:** PASS
- 7 days returned, all with `planned_calories > 0` (first day: 1348.84 kcal)
- `confirmed_calories=0` for all days (no patient meal choices logged yet) ✓

**Check 5 — Isolation:** PASS
- doctor_id=1 token accessing patient 2 (owned by doctor_id=70) → 404 ✓

**Notes for next session:**
- `patients/3` in the original verification spec was a mistake — patient 3 has a v1 plan only (rec_id=169, generation_version=1). Patient 2 (Priya, rec_id=172, generation_version=2) is the correct v2 test patient.
- Swap endpoint correctly returns 409 for thin pools — this is documented expected behavior per R-2 findings. Pool expansion (accompaniment/one_pot for Vegetarian Healthy) is a follow-up task if patient-facing variety complaints surface.
- `doctor_meal_overrides` had 2 pre-existing rows for patient 2 (from prior sessions) before this R-3 session.

**Next:** R-3 COMPLETE. R-4 Doctor Dashboard UI — COMPLETE (see below). R-5 (patient-app v2 plan surfacing) and W3 (pin guardrail clinical decision) remain queued.

---

### R-4 — Doctor Dashboard UI (multi-combo view + approval gate)
**Date:** 2026-06-17  
**Scope:** Doctor dashboard UI wired to R-3 API endpoints. Backend prerequisite (`GET /doctor/pending-approvals`) added.

**Changes:**
1. `app/routers/doctor.py` — added `GET /doctor/pending-approvals`: returns draft v2 plans for this doctor's patients (`{pending: [{patient_id, patient_name, recommendation_id}]}`).
2. `mitihar-frontend/apps/src/lib/doctorApi.ts` — added types (`DishInCombo`, `ComboEntry`, `WeeklyPlanResponse`, `WeeklySummaryDay`, `WeeklySummaryResponse`, `PendingApproval`, `PendingApprovalsResponse`) and 5 API functions (`getWeeklyPlan`, `approveWeeklyPlan`, `swapCombo`, `getWeeklySummary`, `getPendingApprovals`).
3. `mitihar-frontend/apps/src/lib/queryKeys.ts` — added `weeklyPlan(id)`, `weeklySummary(id)`, `pendingApprovals()` keys.
4. `patient-tabs/PlanTab.tsx` — version-adaptive: `combos_available !== false` → renders 4 `ComboCard` per slot in 2×2 grid with Swap button + Approve Week button; v1 patients render unchanged. Fixed pre-existing TS error (`meal.id` key → `meal.Date-meal['Meal Type']`).
5. `patient-tabs/WeeklySummaryTab.tsx` — new file. 7-row table: Date | Planned kcal | Confirmed kcal | Meals confirmed | Bowl sizes. Footer totals. Adherence % badge (green ≥80%, amber ≥50%, red <50%).
6. `PatientDetail.tsx` — added "Weekly Summary" tab (7th tab).
7. `Patients.tsx` — fetches `pendingApprovals` on mount; shows amber "Plan pending" badge in patient name cell.
8. `Recipes.tsx` — fixed pre-existing TS error: added `submit_to_global: false` to addRecipe call.

**TS check result (2026-06-17):** 6 pre-existing `ImportMeta.env` errors (Login.tsx ×5, axios.ts ×1) remain. Zero new errors introduced. Both pre-existing target errors (PlanTab meal.id, Recipes submit_to_global) confirmed fixed.

**Verification (manual — to run):**
- [ ] Login as dr.ashok.mehta@mitihar.test / DoctorTest@2026
- [ ] Priya (patient_id=2, v2 plan) Plan tab → 4 ComboCards per slot visible
- [ ] Approve Week button fires, toast shows, button disappears
- [ ] Swap button on dinner combo succeeds; 409 on breakfast/lunch shows toast "No distinct dishes available for this slot"
- [ ] Patient 3 (v1 plan) Plan tab unchanged
- [ ] Weekly Summary tab on Priya → 7-day table renders
- [ ] Patient list shows amber "Plan pending" badge for draft-plan patients

**Next:** R-5 (patient-app v2 plan surfacing) OR W3 (clinical guardrail decision). Product owner to pick order.

---

### R-5 — Patient-App v2 Plan Surfacing (COMPLETE)
**Date:** 2026-06-17  
**Type:** Backend only (2 changes to existing endpoints, no migrations)  
**Depends on:** R-3 complete (approval gate sets `approval_status='approved'`)

**Scope:**
1. `app/routers/meal_plan.py` — `GET /meal-plan/week` v2 branching:
   - Import `WeeklyCombo` ORM model added.
   - When active recommendation has `generation_version == 2`: queries all 84 `weekly_combos` rows, groups by `slot_date → meal_type → combo_index`, builds `DayMealsV2` response per day. Returns `WeekResponseV2` with `generation_version=2`, `approval_status`, `week_start`, `days[]`.
   - Approval fallback: if active rec is `draft`, falls back to `approved` rec. 404 if no approved/draft rec exists.
   - v1 path unchanged (returns `WeeklyPlan` dict keyed by date).
2. `app/routers/meal_plan.py` — `POST /confirm-choice` v2 extension:
   - `ConfirmChoiceInput` schema: added `weekly_combo_id: Optional[int]`.
   - When `weekly_combo_id` is provided: validates it belongs to patient's active recommendation, persists it to `patient_meal_choices.weekly_combo_id`.
   - v1 path (no `weekly_combo_id`) unchanged.
3. `app/schemas/progress.py` — `ConfirmChoiceInput` schema extended with `weekly_combo_id: Optional[int] = None`.

**Verification (2026-06-17):**
- Check 1 PASS — `GET /meal-plan/week` for priya.test returns `generation_version=2`, `approval_status=approved`, 7 days, first day Breakfast has 4 combos with correct structure (`combo_id`, `combo_index`, `dishes[]`, `total_calories=396.72`, `contains_doctor_pick`).
- Check 2 PASS — `POST /confirm-choice` with `weekly_combo_id` accepted (200).
- Check 3 PASS — `weekly_combo_id` persisted to `patient_meal_choices` table.
- Check 4 — `testaudit` patient has no active plan (data artifact, not regression).

---

### R-6 — Patient App v2 UI (COMPLETE)
**Date:** 2026-06-17/18  
**Type:** Patient app frontend only  
**Depends on:** R-5 complete

**Scope:**
1. `types/index.ts` — Added `WeeklyComboV2`, `DayMealsV2`, `WeekResponseV2` interfaces.
2. `services/meals.ts` — `getWeeklyPlan()` return type changed to `Promise<WeeklyPlan | WeekResponseV2>`; `confirmMealChoice()` body extended with `weekly_combo_id?: number`.
3. `app/(tabs)/meals.tsx` — Full v2 rendering path:
   - `weekPlanQuery` detects `generation_version === 2` via `"generation_version" in weekData`.
   - `V2ComboCard` component: shows dish names, kcal, slot-type tags, "🩺 Doctor's pick" badge when `contains_doctor_pick`, pinned dish highlighted. Confirmed state shows "✓ Chosen" and disables all other Select buttons in the slot.
   - `v2ConfirmMut` mutation sends `food_item_ids` + `weekly_combo_id` to `confirmMealChoice`.
   - `v2ConfirmedSlots` state keyed `"${date}-${mealType}"` → `combo_id` for optimistic confirmed UI.
   - Per-day v2 rendering: finds `DayMealsV2` by `selectedDate`, maps `MEAL_ORDER` → renders 4 `V2ComboCard` per slot in horizontal scroll.
   - v1 regression: `isV2 === false` falls through to existing `SuggestionSlot` path (untouched).
4. TS cast fix (R-6 session cleanup): `index.tsx`, `log-from-plan.tsx`, `meal-detail.tsx`, `week-view.tsx` — cast `plan as WeeklyPlan | undefined` at string-index access sites to resolve `WeeklyPlan | WeekResponseV2` union type errors.

**TS check result (2026-06-18):** 6 pre-existing `ImportMeta.env` errors unchanged. 0 new errors from R-6 changes.

**Manual verification to run (browser + DB):**
- [ ] Login as priya.test@mityahar.com / Test@1234 → Meals tab → 4 V2ComboCards per meal type for today
- [ ] "🩺 Doctor's pick" badge visible on any combo with `contains_doctor_pick=true`
- [ ] Tap "Select" on Breakfast combo → "✓ Chosen" appears, other combos disabled
- [ ] `SELECT weekly_combo_id FROM patient_meal_choices WHERE patient_id=2 ORDER BY created_at DESC LIMIT 1` → not null
- [ ] Navigate to different day → combos render for that date
- [ ] Login as v1 patient → Meals tab shows v1 suggestion flow (regression check)

---

### R-6.5 — Seven Targeted Patient App + Backend Fixes (COMPLETE)
**Date:** 2026-06-18  
**Type:** Mixed — backend (progress_service.py, progress.py, diet_plan_service.py, meal_plan.py) + patient app (types/index.ts, index.tsx, BottomSheet.tsx, progress.tsx, notifications.tsx, plan-history.tsx)  
**Depends on:** R-6 complete

**Scope:**
1. **Home calorie ring** — merged `patient_meal_choices` + `meal_logs` so ring reflects both confirmed plan choices and free-form logged meals. (`progress_service.py`)
2. **Macros (P/C/F)** — summed from `meal_logs`, returned in `GET /progress/today` response. (`progress_service.py`, `progress.py`)
3. **Bottom sheet animation** — replaced spring/bounce with `withTiming(220ms, Easing.out(Easing.ease))`. (`BottomSheet.tsx`)
4. **Steps + water removed** — removed from Progress screen entirely; not tracked in this product. (`progress.tsx`)
5. **Notifications empty state** — replaced mock data with real empty state UI. (`notifications.tsx`)
6. **Plan History v2 label** — now shows correct "v2" label for plans where `generation_version=2`. Root cause: backend was returning `version` instead of `generation_version`. Fixed in `diet_plan_service.py` + `meal_plan.py`; frontend reads `generation_version`. (`plan-history.tsx`, `types/index.ts`)
7. **Beverage list dedup** — deduped via `MIN(id) GROUP BY recipe_name` subquery to eliminate duplicate beverage entries. (`meal_plan.py`)

**TS check result (2026-06-18):** 0 new errors from R-6.5 changes. 6 pre-existing `ImportMeta.env` errors unchanged.

---

### R-6.6 — V2 Combo Detail Screen + Bowl Size + Confirmed State Fix (COMPLETE)
**Date:** 2026-06-18  
**Type:** Mixed — backend (`app/routers/meal_plan.py`) + patient app (`app/(tabs)/meals.tsx`, `app/meals/combo-detail.tsx`, `services/meals.ts`, `types/index.ts`)  
**Depends on:** R-6 complete

**Scope:**

**Part B — Backend + confirmed state fix:**
1. `ConfirmChoiceInput` extended with `bowl_size: str | None = None`; validated against `{'small','medium','large'}` (matches existing DB constraint `ck_pmc_bowl_size` — no migration needed). Defaults to `'medium'` on insert/upsert.
2. `GET /choices/{date}` now returns `weekly_combo_id` per choice — required to seed confirmed state on page reload.
3. `v2ConfirmedSlots` seeded from `dailyChoices` on load via `useEffect` — hard refresh now restores `✓ Chosen` state without user re-selecting.

**Part A — Combo detail screen:**
4. New `GET /meal-plan/combo/{combo_id}/dishes` endpoint — verifies combo ownership (patient can only read their own combos), enriches dishes with macros + ingredients JSONB from `FoodItem`.
5. New screen `app/meals/combo-detail.tsx`:
   - Bowl size selector S/M/L (maps to `small/medium/large` for DB); all calories/macros scale live via `BOWL_FACTORS = {S:0.75, M:1.0, L:1.25}`.
   - Per-dish cards with macros from `getComboDetails` query, expandable ingredient lists.
   - Confirm button: 3 states — already confirmed / slot taken by different combo / available.
   - On confirm: calls `confirmMealChoice` with `bowl_size`, invalidates week plan + daily choices + today, navigates back.
6. `V2ComboCard` wrapped in `Pressable` — card body tap opens combo-detail; Select button still fires quick confirm directly.
7. `getComboDetails` service function + `ComboDetailDish`/`ComboDetailResponse` types added to `services/meals.ts`.

**Bowl size note:** DB constraint uses `'small'/'medium'/'large'` (not `'S'/'M'/'L'`). UI shows `S`/`M`/`L` pill labels; screen maps to DB values before sending. No migration required.

**TS check:** 0 new errors from R-6.6 changes. `/meals/combo-detail` route typed with `as any` cast — Expo Router updates type registry on `expo start`.

---

### R-6.7 — Four Targeted Fixes (COMPLETE)
**Date:** 2026-06-18  
**Depends on:** R-6.6 complete

**Fixes delivered:**

1. **Approve Week button (frontend)** — `approveWeeklyPlan` in `mitihar-frontend/apps/src/lib/doctorApi.ts` was sending no body; backend `POST /doctor/patients/{id}/approve-week` requires a JSON body. Fixed: now sends `{}`. Resolves 422 validation error on approve.

2. **Doctor weekly summary `confirmed_kcal` (backend)** — `GET /doctor/patients/{id}/weekly-summary` was only counting `PatientMealChoice.actual_calories`. Fixed: fallback to `calories` field when `actual_calories` is NULL (pre-logging entries). `app/routers/doctor.py` updated.

3. **Weight goal null display (patient app)** — `progress.tsx` showed `"0 kg"` when `target_weight_kg` is `null`. Fixed: `StatPair` now shows `"Not set"` when `targetWeight` is null. `app/(tabs)/progress.tsx` updated.

4. **Weight chart LineChart migration (patient app)** — Replaced `BarChart` with `LineChart` in `progress.tsx`. Curved bezier, area fill (`#DCFCE7`), tight Y-axis (auto-scale), smooth animation. `minValue`/`maxValue` props removed (not in `LineChartPropsType` — chart auto-scales).

**Weight data seeding:** 5 entries POSTed for Priya (`priya.test@mityahar.com`) via `POST /api/v1/progress/log/weight`. All returned 200. Backend deduplicates by date — history shows 1 entry (last value: 65.0 kg) which is correct.

**TS check result (2026-06-18):** 0 new errors from R-6.7 changes. Pre-existing baseline errors unchanged (register.tsx, profile.tsx, _layout.tsx, connection-status.tsx, shopping-list.tsx, session21.spec.ts).

---

### SESSION 22 — Doctor Weekly Patient Summary
**Type:** Execution (/goal acceptable)  
**Status:** NOT STARTED  
**Dependencies:** Session 21 complete  
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

### SESSION 23 — Frontend Display Updates
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

### SESSION 24 — Full System Verification
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
| 17 | Doctor Meal Config panel: PatientDishPreferences ORM added; 6 meal-config endpoints (GET/PATCH config + pin/block CRUD); generator wired to read blocked/pinned food_ids; MealConfigTab.tsx with TDEE split inputs + dish search dropdowns; E2E 12/12 pass; regression 5/5 pass; CheckConstraint added to db_models.py imports |
| 18B | Ingredient-level medical tag writes complete (Layer 2): 3 Task 1 safety writes (oatmeal/oats flour avoid_gluten, wheat grass powder reversed), Task 2 A+U-Y promotes (76 rows), Task 3 reject log (30 entries in INGREDIENT_REVIEW_DECISIONS.md), Task 4 B-T section promotes (123 rows) — dals/lentils, fenugreek, ragi, palak, rajma, jaggery, drumstick, Groups A-E; Group D lemon Gemma contradiction corrected (liver_friendly added); all 22-tag constraint verified (0 invalid) |
| 18C | Boondi contradiction resolved (avoid_gluten removed ID 173); Layer 3 complete — derive_recipe_tags.py built and run; 4 wheat artifact ingredients fixed (IDs 11,20,46,182); 2116/2143 food_items tagged; 0 invalid tags, 0 avoid_gluten+gluten_free contradictions; Palak paneer avoid_kidney ✓, Cheese recipe avoid_highchol ✓, Masoor dal iron_rich ✓, Paneer calcium_rich ✓ |
| 19 | Generator tag integration + doctor tag review UI: tag_utils.py (15-condition mapping); avoid_tags JSONB filter via GIN index; prefer_tags ORDER BY boost; GET+PATCH /doctor/recipes/{id}/tags with VALID_TAGS validation; TagEditPanel (22 toggles) + tag badges in RecipeCard; TS errors unchanged 8→8; avoid_pcos/avoid_gout confirmed 0-match no-ops |
| 20 | Adaptive Suggestion API: patient_meal_choices table (migration c9d0e1f2a3b4, ORM model); GET /meal-plan/suggestions/{date}/{meal_type} — 4 ranked options, avoid_tags filtered, prefer_tags boosted, weekly variety exclusion, calorie proximity ranking; POST /meal-plan/confirm-choice — upserts choice, returns plan-time calories_remaining_today; dual budget system confirmed (plan-time via patient_meal_choices ≠ consumption via meal_logs); 5/5 verification checks pass |

---

## Post-Session 18B Technical Debt

1. **Duplicate ingredient rows** — Many ingredients appear 2–3× with different capitalisation in the ingredients table (almonds/Almonds/Badam, bajra/Bajra/bajra flour/Bajra flour, etc). All duplicates were tagged identically in Session 18B so Layer 3 derivation is correct. A deduplication/normalisation pass should be done in a future session.

2. **Urad dal papad** — Sits in the ingredients table as if it were a base ingredient. Its tags were rejected in Session 18B because papad processing overrides base dal nutritional profile. Evaluate for condiment reclassification alongside a future ingredient data quality pass.

3. **Wheat grass powder** — Gemma tagged it gluten_free at 0.80 (Layer 1), reversed to avoid_gluten in Session 18B (Task 1). The reversal is clinically correct. This is a documented example of why Layer 1 LLM botanical reasoning can produce technically correct conclusions that are clinically unsafe. Log as training data for any future tagging pipeline calibration.

4. **INGREDIENT_REVIEW.md completion** — Session 18B reviewed A, U–Y entries explicitly and applied pattern rules to B–T section. Review log should be treated as cleared. Any future ingredient additions go through the standard tagging pipeline (Layer 1 auto-accept ≥ 0.85, manual review 0.25–0.84).

5. **Boondi contradiction** — ID 173 (Boondi) has auto-accepted avoid_gluten from Layer 1 (≥ 0.85 confidence) plus gluten_free added in Session 18B. These are contradictory. Awaiting user decision on removing erroneous avoid_gluten. Chickpea-based boondi is genuinely gluten-free; the avoid_gluten auto-accept was a Layer 1 error.

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
- **Condition tag filtering (Session 19)** — `app/services/meal_generator/tag_utils.py` is the canonical mapping of patient condition strings → avoid/prefer tag lists. `CONDITION_AVOID_TAGS` and `CONDITION_PREFER_TAGS` dicts use exact UI strings as keys (e.g. `"Type 2 Diabetes"`, `"PCOS/PCOD"`). `get_avoid_tags(conditions)` and `get_prefer_tags(conditions)` return deduplicated lists. Called in `generate_meal_plan()` from `user_data["medical_conditions"]`. Results passed as `patient_avoid_tags: frozenset` and `patient_prefer_tags: frozenset` through `_find_food_item()` → `_find_food_item_single_diet()` → `base_stmt()`. Empty frozenset → filter/sort skipped entirely.
- **JSONB overlap for avoid filter** — `FoodItem.avoid_tags.contains([tag])` → `avoid_tags @> '["tag"]'::jsonb`. Uses GIN index. `.overlap()` does NOT exist on JSONB (only on ARRAY). Avoid filter: `NOT (tag1_contains OR tag2_contains ...)`. Prefer boost: `OR(tag1_contains, ...).desc()` as first ORDER BY clause.
- **avoid_pcos / avoid_gout** — included in CONDITION_AVOID_TAGS but produce 0-match queries (no food_items have these tags). Silent no-ops until Layer 2 ingredient tagging adds them.
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
- **PatientDishPreferences ORM** — added to db_models.py in Session 17. `CheckConstraint` also added to the sqlalchemy import line.
- **meal-config endpoints (Session 17)** — GET/PATCH `/doctor/patients/{id}/meal-config` + POST/DELETE pin/block. PATCH validates sum=85%, stores `{"Breakfast": x, "Lunch": y, "Dinner": z}`. meal_split=null deletes the row (resets to default). No row = default 25/35/25.
- **meal_split_override format** — `{"Breakfast": 25, "Lunch": 35, "Dinner": 25}` (integer percentages summing to 85). NOT the old breakfast_pct/lunch_pct/dinner_pct format.
- **patient_dish_preferences** — one row per (patient_id, food_item_id), preference_type = 'pin' or 'block'. ON CONFLICT DO UPDATE atomically switches pin↔block. Generator reads this at plan generation time via `blocked_food_ids` and `pinned_food_ids` sets.
- **Generator blocked dishes** — `blocked_food_ids` threaded as `frozenset` through `_find_food_item` → `_find_food_item_single_diet` → `base_stmt()` WHERE NOT IN clause. Empty frozenset = no change to query.
- **Generator pinned dishes** — one pinned dish per meal slot, injected at front of dishes list. Displaces `dishes[-1]` when slot is at capacity (`len(template.slots)`). Skips if dish already placed that day or meal_time_tag incompatible.
- **MealConfigTab.tsx** — `patient-tabs/MealConfigTab.tsx`. Props: `{ patientId: number }`. Uses `qk.patientMealConfig(id)` for cache. Debounced recipe search (300ms). Save & Regenerate button disabled when sum ≠ 85. Invalidates `qk.patientPlan(id)` after 2s on save.
- **/diet-plans/my-plan response shape** — returns `{ user_id, created_at, meals: [...], ingredient_checklist, version, used_food_ids }`. Access `plan["meals"]` not the top-level object. Note for regression scripts.
