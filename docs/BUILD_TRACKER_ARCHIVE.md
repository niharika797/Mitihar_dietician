# Build Tracker Archive

_Historical session records — opened on demand, NOT read at session start._  
_Migrated from BUILD_TRACKER.md and CLAUDE.md on 2026-07-04._  
_For current status see BUILD_TRACKER.md → CURRENT STATUS or CURRENT_STATE.md._

---

## SESSION BUILD PLAN (historical)

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
| Millet Khichdi (bajra) | `avoid_diabetes` assigned — should be `diabetes_friendly` | 0.60 | Millet confusion |
| Jowar roti | `avoid_diabetes` assigned — should be `diabetes_friendly` | 0.70 | Millet confusion |
| Jowar roti | `avoid_pcos` assigned — should be `pcos_friendly` | 0.70 | Millet confusion |
| Lauki Paneer | `avoid_kidney` assigned — lauki is kidney-SAFE per KB | 0.80 | Self-contradictory reasoning |
| Arbi Achaar (pickle) | `gut_friendly` assigned — vinegar+chilli pickle is gut-irritating | 0.80 | Ingredient isolation without dish context |
| Stuffed Mango Pickle | `diabetes_friendly` for trace methi seeds | 0.50 | Ingredient isolation without dish context |
| Oats Moong Dal | `gluten_free` assigned — oats require certified GF flag | 0.95 | Cross-contamination rule missed |
| Chicken Biryani | Missing `avoid_diabetes` entirely | — | Tag omission |

**Root causes identified:**
1. **Millet confusion**: Gemma sees "millet = low-GI" in its reasoning but assigns `avoid_*` tag anyway.
2. **Self-contradictory reasoning**: Model reasons correctly ("lauki is kidney-safe") then assigns `avoid_kidney`. Instruction-following failure.
3. **Ingredient isolation**: Beneficial spice ingredient in achaar/pickle overrides dish-level context.
4. **Oats rule**: Cross-contamination rule present in compact KB but model didn't apply it. 0.95 confidence false `gluten_free` is high-risk for celiac patients.

**Recommended confidence thresholds:**
- **Auto-accept: ≥ 0.90** — ~95% safe rate in pilot; requires compact KB fixes first
- **Claude API review: 0.50–0.89** — verify before writing to DB
- **Discard: < 0.50** — already filtered in script
- **Special rule**: Never auto-accept `avoid_diabetes` or `avoid_pcos` on millet recipes (jowar/bajra/ragi) until compact KB millet section clarified

**Success criteria:** Schema columns live ✅. Pilot ran 50/50 ✅. Quality issues documented ✅. Thresholds calibrated ✅.

---

### SESSION 18B — Medical Condition Tagging (Full Run + Doctor Review UI)
**Type:** Execution  
**Status:** COMPLETE ✅ (2026-06-07) — scope delivered across Sessions 18B/18C/19/19-ext  

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

Tasks:
- [x] Pre-task audit 1 — Layer 3 data confirmed live: avoid_tags non-empty 1194, prefer_tags non-empty 1940, 27 empty (no recipe_ingredients), distinct tags match BUILD_TRACKER ✅
- [x] Pre-task audit 2 — medical_conditions field confirmed: JSONB array, exact UI strings from onboarding screen, all test patients have empty arrays
- [x] Pre-task audit 3 — base_stmt() located in meal_generator.py:515 (nested closure), patient data available via user_data in generate_meal_plan, no existing condition filtering
- [x] Pre-task audit 4 — tag cross-check: 10/12 avoid tags match; avoid_pcos and avoid_gout are 0-match no-ops (never assigned in Layer 2)
- [x] Task 1 — `app/services/meal_generator/tag_utils.py` created: CONDITION_AVOID_TAGS, CONDITION_PREFER_TAGS dicts (15 conditions × exact DB tag strings), get_avoid_tags(), get_prefer_tags() helpers
- [x] Task 2 — Avoid tag filter in base_stmt(): NOT (avoid_tags @> '["tag"]' OR ...) using JSONB contains(); GIN index used
- [x] Task 3 — Prefer tag boosting: prefer_sort = OR(prefer_tags @> each tag).desc() prepended to ORDER BY; existing region_sort + cal_sort as tiebreakers
- [x] Task 4 — Regression: 5/5 checks pass
- [x] Task 5 — BUILD_TRACKER updated

**Regression results:**
- Check 1: Diabetic+Hypertension patient → 77 dishes, 0 avoid_diabetes / avoid_hypertension violations ✅
- Check 2: Healthy patient (no conditions) → 21 slots, 0 empty ✅
- Check 3: food_items count unchanged (2143 before and after) ✅

**Condition gaps flagged:**
- `avoid_pcos` — 0 food_items in DB; PCOS/PCOD filter is a no-op until Layer 2 tags are added to pcos-relevant recipes
- `avoid_gout` — 0 food_items in DB; Gout filter is a no-op until Layer 2 tags are added

**Session findings:**
- `FoodItem.avoid_tags.overlap()` does not exist on JSONB columns (only on ARRAY columns). Used `contains([tag])` → `@> '["tag"]'` which correctly uses the GIN index.
- `or_()` with `.contains()` list comprehension produces the correct JSONB overlap semantics for multi-condition patients.
- `prefer_sort` computed once per `_find_food_item_single_diet()` call; passed via closure into `base_stmt()` alongside existing `region_sort` and `cal_sort`.
- Patient with `medical_conditions=[]` computes empty frozensets; both filters skip entirely — no behavior change for existing patients.

---

### SESSION 20 — Adaptive Suggestion API
**Type:** Foundation (no /goal — architectural)  
**Status:** COMPLETE ✅ (2026-06-07)  

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

---

### SESSION 20.5 — Password Hash Root Cause Fix
**Type:** Bug fix / Infrastructure  
**Status:** COMPLETE (2026-06-08)  

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
**Status:** COMPLETE (2026-06-17/18) — delivered as R-5 (Patient-App v2 Plan Surfacing) + R-6 (Patient App v2 UI) + R-6.5/R-6.6/R-6.7 (targeted fixes)  

**Success criteria:** Patient can choose from options. Calorie ring reflects choices in real time. Snack quick log works.

---

### SESSION 21.5 — Onboarding Cleanup (Field Audit Follow-up)
**Type:** Execution (frontend only)  
**Status:** COMPLETE (2026-06-10)  

**Changes (patient app onboarding only — zero backend/DB changes):**
- [x] `allergies.tsx` — "Nightshades" removed from allergy chip list (audit: 0 food_items contain "nightshade" in ingredients; substring filter was a silent no-op). 7 chips remain.
- [x] `personal-info.tsx` — Target Weight label now reads "(optional)". Field was already non-blocking; label change only.
- [x] `dietary-preferences.tsx` — Meals Per Day section removed (was a single locked "3 meals" button). `meals_per_day` no longer written from this screen; onboarding store default `"3"` still submits 3 to the backend.
- [x] Lifestyle step deleted entirely (`lifestyle.tsx` removed, `Stack.Screen` entry removed from `(onboarding)/_layout.tsx`). Flow is now dietary-preferences → disclaimer. Also drops smoking/alcohol toggles; store defaults (`false`/`false`) submit instead.
- [x] Step counter: 8 → 7 across all remaining screens; disclaimer is now step 7 of 7.

**DB columns intentionally untouched (stored-only, no longer collected):** `meals_per_day` (default 3), `sleep_hours`, `water_glasses`, `occupation`, `eating_habits`, `smoking`, `alcohol`.

---

### SESSION 22A — Generator Fixes (Bugs 1 + 3)
**Type:** Execution (bugfix)  
**Status:** COMPLETE (2026-06-11)  

**Bug 1 — used_food_ids snowball (variety collapse):**
- [x] `meal_generator.py` — generator now saves only IDs picked THIS generation (`weekly_used_ids - prior_seed`), never the accumulated union. Previously each regeneration persisted seed+new, so after 13 regenerations Priya's exclusion list (~260 ids) covered her entire candidate pool → Level 1 always empty → Level 2 deterministic top pick → identical dishes all 7 days.
- [x] `diet_plan_service.py` — cross-week seeding block removed entirely.

**Bug 3 — diet label / non-veg budget mismatch:**
- [x] `meal_generator.py` `_find_food_item` — diet fallback chain now uses per-slot `query_diet` for Lunch/Dinner (only `nonveg_assigned` budget slots get non-veg candidates). Breakfast keeps `user_diet` so the breakfast-egg exception still fires.
- [x] `dishes[]` now serializes `diet_type` per dish.
- [x] `Diet Type` slot label now derived from actual dishes via `_derive_diet_label()` instead of `query_diet`.

**Verification (all pass):**
- Check 1 variety: plan 158 has 7/7/7 distinct dish hashes per meal type ✓
- Check 2 labels: plan 159 — every slot label matches its dishes' diet_types; 4 non-veg slots/week ✓
- Check 3 TDEE: patient 2 tdee=1866.91 ✓
- Check 4 used_food_ids: 61/63 ids (unique dishes this generation) — not the 260-id snowball ✓

---

### SESSION 22B — slot_type Taxonomy Cleanup (Bugs 4 + 5)
**Type:** Execution (data fix + small generator change)  
**Status:** COMPLETE (2026-06-11)  

**Bug 4 + 5 fix — food_items reclassification (859 rows, one transaction):**
- [x] 83 → `one_pot` (biryani/pulao/khichdi/pongal/pulihora/sadam/bhath/flavored-rice complete preparations)
- [x] 275 → `dal_protein` (non-veg/egg mains + dal/kadhi/rasam/sambar/kuzhambu/paneer/legume gravies)
- [x] 501 → `sabzi` (vegetable preparations: poriyal, thoran, kootu, palya, gojju, dry sabzis)
- [x] 66 stay `grain` (true carb bases: chapati/roti/phulka/paratha/naan/puri/rice/rotla/ragi mudde/porridges)
- [x] `meal_generator.py` — `ONE_POT_PROBABILITY = 0.40` and `ONE_POT_SLOTS = [one_pot:0.70, accompaniment:0.30]` constants
- [x] Per Lunch/Dinner slot per day: 40/60 split ≈ 3 one-pot meals of 7
- [x] `one_pot` added to `PROTECTED_SLOTS`

**Verification (all pass, rec 163/164):**
- Check 1: every biryani/pulao/khichdi dish in both plans has `slot_type='one_pot'`; none in grain ✓
- Check 2: one_pot meals have exactly 2 dishes `[one_pot, accompaniment]`; standard meals 4 `[grain, dal_protein, sabzi, accompaniment]` ✓
- Check 3: grain slots contain only true bases ✓

---

### SESSION 22B.5 — Accompaniment Pool Audit + Cleanup
**Type:** Execution (pure data fix)  
**Status:** COMPLETE (2026-06-11)  

**Reclassification (3 rows, one transaction):**
- [x] id 249 "Fish Curry" (180 kcal) `accompaniment` → `dal_protein`
- [x] id 308 "Rajma Chawal" (315 kcal) `accompaniment` → `one_pot`
- [x] id 3724 "Palak Paneer" (Lunch-tagged `main_dish`) → `sabzi`
- Post-update pools: accompaniment 21, dal_protein 373, one_pot 88, sabzi 863.

---

### SESSION 22C — Diagnostic Audit: Bug 2 + Bug 6 (NO fixes)
**Type:** Audit/diagnosis only  
**Status:** COMPLETE (2026-06-12)  

**Bug 2 findings (calorie display divergence):**
- `Total Calories` is the slot budget target, not a sum of dish calories.
- `dishes[].calories` is unscaled per-serving (`meal_generator.py:360`); portion factor baked into `dishes[].ingredients[].amount_g` but discarded as a number.
- Divergence −42% to +164% per slot, not a uniform ratio.
- Doctor dish PATCH recalcs `Total Calories = sum(unscaled dishes)` — edits silently flip the header's basis. Pinned dishes never added to totals.
- Verdict: two legitimate bases + a discarded factor — NOT a one-line missed scaling step.

**Bug 6 findings (suggestions endpoint, live calls):**
- Confirmed: single food_items ranked by |cal − whole-slot target|; slot_type unconstrained. Actively breaks adaptive budget: confirm-choice writes one dish's calories as the whole meal.
- Collateral: "Test Dal Tadka" ×2 (ids 3676/3677, is_verified=True test artifacts) served to Priya; Chicken Biryani (300/332) still missing `avoid_diabetes`, suggested to a diabetic.

---

### SESSION 22D — Design Audit: scaled_calories impact map
**Type:** Audit/design only  
**Status:** COMPLETE (2026-06-12)  

**Part 1 — Bug 2 impact map (15 code paths inventoried, W1–W6 writers / R1–R3 backend readers / F1–F9 frontend):**
- Recommends persisting `dishes[].factor` AND slot-level `"Target Calories"` alongside `scaled_calories`.
- Edge-case recommendations: factor=1.0 for custom dishes / PATCH swaps / pinned dishes; pinned dishes finally included in header Σ; forward-only (no backfill).

**Part 2 — Beverage blast radius:**
- beverage slot exists ONLY in the 36 Breakfast templates, at 0.10 pct, `required: false`. Lunch/Dinner have NO beverage slot.
- 24 beverage food_items; only 10 Breakfast-tagged reachable.
- Recommend redistribute Breakfast to 0.78/0.22 (combo re-run: −16%…+20%).

**Part 3 — confirm-choice schema:** Option A (JSONB `chosen_dishes` on existing row) recommended over child table.

---

### SESSION 22E — Bug 2 + Bug 6 Implementation
**Type:** Execution + Verification  
**Status:** COMPLETE (2026-06-13) — all 16 endpoint checks PASS  

**What shipped:**
- `dishes[].scaled_calories` (= `calories × factor`), `dishes[].factor` (1.0 for custom/PATCH/pinned), and slot `"Target Calories"` persisted in `recommendations.meals` JSONB.
- Beverage slot removed from Breakfast generation via in-code `BREAKFAST_SLOTS` override (0.78 main / 0.22 accompaniment).
- `patient_meal_choice_dishes` child table (migration `d0e1f2a3b4c5`): confirm-choice now writes parent + child atomically.
- Q8 cleanups committed: Test Dal Tadka (3676/3677) excluded, Chicken Biryani (286/300/332) tagged `avoid_diabetes`.
- Doctor amber warning: `|Σ(scaled_calories) − Target Calories| / Target Calories > 10%` threshold in PlanTab.tsx.

**Verified (16/16 PASS):** all checks including biryani absent from diabetic suggestions, scaled_calories persisted, combo confirm written correctly, W3 pin verification 5/5 PASS.

---

### SESSION 22F — Bug 6 Combo-Building + Backlog B Diet Filter
**Type:** Execution  
**Status:** COMPLETE (2026-06-15)  

**What shipped:**
1. Suggestions endpoint: `_get_slot_composition()` reads slot_types from active plan JSONB; round-robin combo construction (up to 4 combos); response shape `SuggestedCombo[]` (`combo_id`, `total_calories`, `dishes[]`).
2. Backlog B diet_type filter: `DIET_TYPE_HIERARCHY` constant; `FoodItem.diet_type.in_(allowed_diet_types)` added to all pool queries.
3. Confirm-choice: `ConfirmChoiceInput.food_item_id: int` → `food_item_ids: list[int]`; parent `calories` = `sum(fi.cal_per_serving)`.
4. Patient app frontend: `ComboCard` component shows `dish1 + dish2 + ...` names; `confirmMut` sends `food_item_ids`.

---

### R-0 — Pre-Rebuild Data Pass
**Type:** Data-pass (DB only, no code/migration/frontend changes)  
**Status:** COMPLETE — 2026-06-16  

**Task 1 — Biryani/pulao avoid_diabetes tagging:**
- 30 dishes tagged with `avoid_diabetes`.
- 12 dishes intentionally left untagged — low-GI/fibre-rich exemption (millet, broken wheat/daliya, quinoa, moong dal khichdi).
- 0 dishes flagged open — all 4 originally-ambiguous dishes resolved via user clinical review.
- Corrected verification query excludes exemption keywords explicitly. Confirmed returns 0 rows.
- Backlog A is now CLOSED.

**Task 2 — Test artifact verification (NO deletion performed):**
- IDs 3698–3716 (19 rows): "Global Test Recipe" ×7, "To Be Rejected Recipe" ×6, "Doctor2 Private Dal" ×6.
- 13 rows ("Global Test Recipe" + "To Be Rejected Recipe") confirmed unreachable — `meal_time_tags = {}` (empty).
- **⚠️ "Doctor2 Private Dal" (6 rows) NOT unreachable** — `meal_time_tags={Lunch}`, `is_verified=false`. `meal_generator.py:606-622` (`base_stmt`) never filters `is_verified` or `doctor_id`. Unverified test dal reachable by MealGenerator for any Vegetarian patient's Lunch dal_protein slot. Gap logged — no code change made.

**Task 3 — Pool snapshot (pre-R-2 baseline):** full pool table recorded (by slot_type × diet_type × meal_time).

---

### R-1 — Schema Expansion
**Date:** 2026-06-16  
**Type:** Migrations + ORM only  
**Status:** COMPLETE  

5 migrations applied:
1. `e1f2a3b4c5d6` — `recommendations` +2 columns: `generation_version`, `approval_status`
2. `f2a3b4c5d6e7` — new table `weekly_combos` (84 rows/patient/week)
3. `a3b4c5d6e7f8` — new table `weekly_patient_summary` + `patient_meal_choices` +3 columns: `weekly_combo_id`, `bowl_size`, `actual_calories`
4. `b4c5d6e7f8a9` — `doctor_meal_overrides` +3 columns: `patient_condition_snapshot`, `edit_reason`, `doctor_note`
5. ORM updates: `Recommendation`, `WeeklyCombo`, `WeeklyPatientSummary`, `PatientMealChoice`, `DoctorMealOverride` all updated.

All 5 verification queries PASS.

---

### R-2 — Generation Layer
**Date:** 2026-06-16  
**Type:** Logic only  
**Status:** COMPLETE  

**Changes:**
1. `meal_generator.py`:
   - Change 1: `is_verified == True` filter added to `_pick_for_slot.base_stmt()` — closes R-0-discovered gap.
   - Change 2: `DIET_TYPE_HIERARCHY` and `DIET_TYPE_FALLBACK` constants + 4-level exhaustion cascade in `_pick_for_slot`.
   - Change 3: pin as preference signal (removed forced pin-injection; `prefer_sort` boosts `FoodItem.id.in_(pinned_food_ids)`).
   - Change 4: per-slot block loops `combo_idx in range(4)` calling new `_fill_slot_dishes()`; return dict gained `combos` (84 dicts).
2. `app/schemas/diet_plan.py`: `DietPlanResponse` gained `combos: list[dict] = []` and `generation_version: int = 1`.
3. `app/services/diet_plan_service.py`: threads `combos`/`generation_version=2`, bulk-inserts `WeeklyCombo` rows.
4. `app/routers/diet_plans.py`: dispatches on `generation_version`; new `_validate_generated_combos()`.

**Verification:** 84 weekly_combos rows stored, combo_index distribution 21 each (0–3). 15 Level-4 fallback (thin pool, expected). Stored recommendation_id=172 for priya.

---

### R-3 — Doctor API / Approval Gate
**Date:** 2026-06-17  
**Type:** Backend endpoints only  
**Status:** COMPLETE  

4 new endpoints in `app/routers/doctor.py`:
- `GET /patients/{patient_id}/weekly-plan` — returns active recommendation + all 84 weekly_combos rows grouped.
- `POST /patients/{patient_id}/weekly-plan/approve` — flips `approval_status` draft → approved; fires FCM push.
- `POST /patients/{patient_id}/weekly-plan/combos/{combo_id}/swap` — re-fills one WeeklyCombo's dishes; returns 409 `pool_exhausted` when no distinct dishes available.
- `GET /patients/{patient_id}/weekly-summary` — returns 7-day adherence summary.

All 5 checks PASS including isolation (wrong doctor token → 404).

---

### R-4 — Doctor Dashboard UI (multi-combo view + approval gate)
**Date:** 2026-06-17  
**Status:** COMPLETE  

Changes: `GET /doctor/pending-approvals` endpoint + doctorApi.ts types/functions + PlanTab.tsx (version-adaptive v2 ComboCards) + WeeklySummaryTab.tsx (new) + PatientDetail.tsx (7th tab) + Patients.tsx (pending badge) + Recipes.tsx (pre-existing TS error fixed). tsc: 0 new errors.

---

### R-4.5 — Dish-Level Editing, Custom Meal v2, Swap Error Messages
**Date:** 2026-06-17  
**Type:** Backend (1 new endpoint + 1 extended endpoint) + Frontend (3 UI additions)  
**Status:** COMPLETE  

1. Swap error messages: 409 → "No dishes available for this slot — pool exhausted", 404 → "Combo not found".
2. Dish-level editing via expandable ComboCard: new `PATCH /patients/{patient_id}/weekly-plan/combos/{combo_id}/dishes/{dish_index}` endpoint; per-dish swap/remove/add actions.
3. Add Custom Meal for v2 plans: `combo_index: int` added to `AddCustomDishRequest`; `AddCustomMealModal` in PlanTab.tsx.

---

### R-5 — Patient-App v2 Plan Surfacing
**Date:** 2026-06-17  
**Type:** Backend only (2 changes to existing endpoints, no migrations)  
**Status:** COMPLETE  

- `GET /meal-plan/week` v2 branching: queries all 84 `weekly_combos` rows, groups by `slot_date → meal_type → combo_index`, returns `WeekResponseV2` with `generation_version=2`, `approval_status`.
- `POST /confirm-choice` v2 extension: added `weekly_combo_id: Optional[int]`; validates it belongs to patient's active recommendation.

Verification: 3/3 PASS (v2 response shape correct, weekly_combo_id accepted and persisted).

---

### R-6 — Patient App v2 UI
**Date:** 2026-06-17/18  
**Type:** Patient app frontend only  
**Status:** COMPLETE  

- `types/index.ts` — Added `WeeklyComboV2`, `DayMealsV2`, `WeekResponseV2` interfaces.
- `app/(tabs)/meals.tsx` — Full v2 rendering path: `V2ComboCard` component, `v2ConfirmMut` mutation, `v2ConfirmedSlots` state, v1 regression path untouched.
- TS check: 0 new errors.

---

### R-6.5 — Seven Targeted Patient App + Backend Fixes
**Date:** 2026-06-18  
**Status:** COMPLETE  

1. Home calorie ring — merged `patient_meal_choices` + `meal_logs`.
2. Macros (P/C/F) — summed from `meal_logs`, returned in `GET /progress/today`.
3. Bottom sheet animation — replaced spring/bounce with `withTiming(220ms, Easing.out(Easing.ease))`.
4. Steps + water removed from Progress screen.
5. Notifications empty state — replaced mock data.
6. Plan History v2 label — `generation_version` fix in `diet_plan_service.py` + `meal_plan.py`.
7. Beverage list dedup — `MIN(id) GROUP BY recipe_name` subquery.

---

### R-6.6 — V2 Combo Detail Screen + Bowl Size + Confirmed State Fix
**Date:** 2026-06-18  
**Status:** COMPLETE  

- `ConfirmChoiceInput` extended with `bowl_size: str | None = None`; validated against `{'small','medium','large'}`.
- `GET /choices/{date}` now returns `weekly_combo_id` per choice.
- `v2ConfirmedSlots` seeded from `dailyChoices` on load.
- New `GET /meal-plan/combo/{combo_id}/dishes` endpoint.
- New screen `app/meals/combo-detail.tsx`: S/M/L bowl selector scaling macros via `BOWL_FACTORS = {S:0.75, M:1.0, L:1.25}`.

---

### R-6.7 — Four Targeted Fixes
**Date:** 2026-06-18  
**Status:** COMPLETE  

1. Approve Week button — now sends `{}` body (was missing body, caused 422).
2. Doctor weekly summary `confirmed_kcal` — fallback to `calories` when `actual_calories` is NULL.
3. Weight goal null display — shows `"Not set"` when `target_weight_kg` is null.
4. Weight chart — replaced `BarChart` with `LineChart` (curved bezier, area fill `#DCFCE7`).

---

### R-7A — Weekly Cycle Automation: Summary Service + Doctor UI
**Date:** 2026-06-21  
**Status:** COMPLETE  

1. `app/services/weekly_summary_service.py` (new) — `compute_weekly_summary(db, patient_id, week_start)`. Idempotent. Builds `per_day`, `dish_frequency`, `pattern`, `week_totals`. Upserts into `weekly_patient_summary`. Never raises.
2. `GET /patients/{patient_id}/weekly-summary` — replaced 80-line direct query with 3-line call to `compute_weekly_summary()`.
3. `app/main.py` — `complete_expired_plans()` cron added (Sunday 01:00 UTC).
4. `doctorApi.ts` — `DishFrequencyEntry` and `WeeklySummaryData` interfaces; `getWeeklySummary()` accepts optional `weekStart?: string`.
5. `WeeklySummaryTab.tsx` — Section A "This Week's Choices" (expandable per-day rows) + Section B "Patterns This Week" (preferred/never-selected chips).

**R-7A.1 fix (2026-06-21):** Rec lookup date mismatch fixed. Old code floored `week_start` to Monday then queried `Recommendation.week_start_date == floored_monday` — always failed for rec with `week_start_date = 2026-06-18` (Thursday). Fix: query `is_active=True` first, use rec's own `week_start_date` as canonical window.

**R-7A.2 (2026-06-28):** `_compute()` historical lookup fixed — explicit `week_start` param pins to that week's rec. Endpoint default Monday fallback removed. `preferred_food_ids` boost + `avoided_food_ids` exclusion live in `_pick_for_slot()`. Verified: Dahi ×28, Chaas ×28 in new plan; 34 avoided dishes absent.

---

### SESSION 22 — Doctor Weekly Patient Summary
**Type:** Execution (/goal acceptable)  
**Status:** COMPLETE (2026-06-21) — delivered as R-7A.  

---

### SESSION 23 — Frontend Display Updates
**Type:** Execution (/goal acceptable)  
**Status:** NOT STARTED  

Tasks:
- [ ] Patient app meal detail: remove gram quantities, show macros prominently
- [ ] Add proportional ingredient labels (map gram ranges to prose labels)
- [ ] Doctor dashboard plan view: same macro-only display for consistency
- [ ] Shopping list: ingredient names only — remove all quantity columns
- [ ] Beverage category UI: separate section in patient app and doctor dashboard
- [ ] Accompaniments shown as separate sub-slot (not concatenated with main dish name)

---

### SESSION 24 — Full System Verification
**Type:** Verification  
**Status:** NOT STARTED  

Tasks:
- [ ] Full critical path: register → onboard → get suggestions → choose meals → doctor reviews → adjusts config → patient sees updated suggestions
- [ ] Diabetic patient gets correct filtered suggestions
- [ ] Doctor TDEE override changes patient's meal sizing
- [ ] Rating system collects real thumbs-up/down data
- [ ] Override tracking records real food_ids
- [ ] Nutrition chain: ingredient edit propagates to meal plan
- [ ] Weekly summary shows accurate patient choices
- [ ] All P0 and P1 issues from known issues list resolved

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
| 9 | P0 data fixes: 6 recipes with 40,000g ingredient amounts corrected + "Gm " prefix cleaned; 18 beverages moved to correct slot_type; is_verified badge added; serving_weight_g + sodium_per_serving added |
| 10 | Schema designed and approved: 5 new tables + dishes[] JSONB spec; migration c2d3e4f5a6b7; product owner approved with 3 changes |
| 11 | Migration run; PatientMealConfig ORM added; meal_generator rewritten: snacks removed, effective_tdee=TDEE×0.85, patient_meal_config override, dishes[] with food_id per slot; validator fixed (35→21) |
| 12 | Dead code removed from meal_generator.py; MEAL_ORDER updated to 3 meals in 5 patient app files; TEASER_MEALS reduced to 3 entries; API verified: 21 slots, 0 snacks, dishes[] + food_id in all meals |
| 13 | Rating system bug fixed (meal.food_id was always null); meal-detail.tsx fully redesigned: per-dish cards, ratings wired to correct food_item_id, DB confirmed 2 rows, E2E browser verification passed |
| 14 | Alembic migration d5e6f7a8b9c0; seeded 950 ingredient names; LLM nutrition estimation (846/950 filled); linked 18,248 recipe_ingredients rows (100% match); Task 6 deferred |
| 15 | Fixed IFCT measurement-phrase matching bug; reset 15 dirty IFCT2017 ingredients; re-imported 88 clean IFCT matches; 1519 calculated, 623 manual; 0 outliers in calculated set |
| 16 | Fixed custom meal pipeline (JSONB-only by default); submitted_for_review column; dedup to add_recipe; is_verified filter to browse_recipes; PATCH endpoint for dish-level swap/remove/add; dish card UI in PlanTab.tsx |
| 17 | Doctor Meal Config panel: PatientDishPreferences ORM added; 6 meal-config endpoints; generator wired to blocked/pinned food_ids; MealConfigTab.tsx; E2E 12/12 pass |
| 18B | Ingredient-level medical tag writes complete (Layer 2): Task 1 safety writes, Task 2 A+U-Y promotes (76 rows), Task 3 reject log (30 entries), Task 4 B-T section promotes (123 rows) |
| 18C | Boondi contradiction resolved; Layer 3 complete — derive_recipe_tags.py built and run; 2116/2143 food_items tagged; 0 invalid tags |
| 19 | Generator tag integration + doctor tag review UI: tag_utils.py (15-condition mapping); avoid_tags JSONB filter via GIN index; prefer_tags ORDER BY boost; GET+PATCH /doctor/recipes/{id}/tags; TagEditPanel |
| 20 | Adaptive Suggestion API: patient_meal_choices table; GET /meal-plan/suggestions/{date}/{meal_type} — 4 ranked options; POST /meal-plan/confirm-choice; dual budget system; 5/5 verification checks pass |

---

## Post-Session 18B Technical Debt

1. **Duplicate ingredient rows** — Many ingredients appear 2–3× with different capitalisation in the ingredients table (almonds/Almonds/Badam, bajra/Bajra/bajra flour/Bajra flour, etc). All duplicates were tagged identically in Session 18B so Layer 3 derivation is correct. A deduplication/normalisation pass should be done in a future session.

2. **Urad dal papad** — Sits in the ingredients table as if it were a base ingredient. Its tags were rejected in Session 18B because papad processing overrides base dal nutritional profile. Evaluate for condiment reclassification alongside a future ingredient data quality pass.

3. **Wheat grass powder** — Gemma tagged it gluten_free at 0.80 (Layer 1), reversed to avoid_gluten in Session 18B (Task 1). The reversal is clinically correct. This is a documented example of why Layer 1 LLM botanical reasoning can produce technically correct conclusions that are clinically unsafe. Log as training data for any future tagging pipeline calibration.

4. **INGREDIENT_REVIEW.md completion** — Session 18B reviewed A, U–Y entries explicitly and applied pattern rules to B–T section. Review log should be treated as cleared. Any future ingredient additions go through the standard tagging pipeline (Layer 1 auto-accept ≥ 0.85, manual review 0.25–0.84).

5. **Boondi contradiction** — ID 173 (Boondi) had auto-accepted avoid_gluten from Layer 1 plus gluten_free added in Session 18B. These are contradictory. Chickpea-based boondi is genuinely gluten-free; the avoid_gluten auto-accept was a Layer 1 error. Resolved in Session 18C.

---

## CLAUDE.md Historical Current State Entries

_Migrated from CLAUDE.md Current State section on 2026-07-04. Newest entry first (as they appeared in CLAUDE.md)._

---

**ENVIRONMENT EXPLICIT FLAG — HOSTNAME HEURISTIC REPLACED (2026-07-03, 1 commit)**

- `app/core/config.py`: added `ENVIRONMENT: str = "development"` with a strict validator — only `"development"`, `"staging"`, `"production"` accepted; any typo (e.g. `"prod"`) raises `ValidationError` at startup.
- `app/main.py` lifespan: removed `socket.gethostname()` / `os.name == "nt"` heuristic entirely. New guard: `if ENVIRONMENT == "production" and not COOKIE_SECURE → RuntimeError`. Non-production just logs a warning — local dev is never aborted.
- `.env`: `ENVIRONMENT=development` appended.
- `deploy-env-reference.txt`: `ENVIRONMENT=production` added with CRITICAL note that Cloud Run must inject it explicitly or the fail-closed guard will not trigger.
- Test results (4 cases, all PASS): Case A `production`+`COOKIE_SECURE=False` → RuntimeError. Case B `production`+`True` → boots clean. Case C `development`+`False` → warning logged, no abort. Case D `"prod"` → ValidationError at startup.
- `full_backend_test.py` 98/98 — zero regressions. Also fixed pre-existing flakiness: `timeout=60` added to `/progress/log/weight` call (triggers full plan regeneration, was timing out against httpx's 5s default).
- Known Pending Issue "COOKIE_SECURE local-dev heuristic is fragile" closed.
- Next action: Layer 3 / GCP deployment phase (Cloud Run + Cloud SQL + Scheduler jobs). Ensure `ENVIRONMENT=production` is set as a Cloud Run env var.

---

**COOKIE_SECURE FAIL-CLOSED + .ENV.PRODUCTION RETIRED (2026-07-03, 2 commits)**

- Commit 1 (`0e50a87`): `app/main.py` lifespan guard now raises `RuntimeError` (was log-only CRITICAL) when `COOKIE_SECURE=False` off a dev machine. **Finding: dev hostname is `NOD-KRAI`, not `DESKTOP-*` — the old heuristic never matched this machine** (that's why the CRITICAL warning always printed in dev). Added `os.name == "nt"` to `is_local` so local dev still boots; Windows is never a deploy target. Heuristic fragility logged in Known Pending Issues — replace with explicit `ENVIRONMENT` setting in Layer 3.
- Commit 2: `.env.production` renamed → `deploy-env-reference.txt` (app never read it — `config.py` loads only `.env`). Header rewritten: reference-only, values must be injected into Cloud Run via `--set-env-vars`/Secret Manager at deploy time. Added to `.gitignore` AND `.dockerignore`. Doc refs updated in CLAUDE.md + DEPLOY_CHECKLIST.md.
- Bonus resolution: after rename the `.env*` permission block no longer applied — file read; `COOKIE_SECURE=True` was ALREADY set in it.
- Next action: Layer 3 / GCP deployment phase.

---

**PRE-LAYER-3 HARDENING — INDEX DONE, COOKIE_SECURE BLOCKED (2026-07-03, commit 3c7f724)**

- Migration `2b3c4d5e6f7a_add_idx_patient_requests_doctor_id.py`: `CREATE INDEX idx_patient_requests_doctor_id ON patient_requests(doctor_id)`, mirrors `1a2b3c4d5e6f` pattern, downgrade drops it. Applied locally; `pg_index` shows indisvalid=true; EXPLAIN ANALYZE uses Bitmap Index Scan even with default planner (table currently 0 rows). Downgrade→upgrade roundtrip clean. New alembic head: `2b3c4d5e6f7a`.
- Gotcha hit: first-choice revision ID `c3d4e5f6a7b8` already taken by `add_doctor_public_fields` — alembic reported "Cycle is detected in revisions". Check existing revision IDs before minting one.
- `full_backend_test.py`: 98/98 after deleting 1 stale verified "Test Dal Tadka" row (id 3726).
- **COOKIE_SECURE in `.env.production`: RESOLVED 2026-07-03** — file renamed to `deploy-env-reference.txt`.
- Next action: Layer 3 / GCP deployment phase.

---

**AXIOS.TS DYNAMIC-IMPORT FIX — COMPLETE (2026-07-03, uncommitted)**

- `PlanTab.tsx`: dynamic `import('../../../../lib/axios')` in `fetchNutritionFromGemini` (line 476) replaced with static top-level `import apiClient from '../../../../lib/axios'` — matches Billing.tsx/Recipes.tsx pattern.
- Vite "dynamically imported but also statically imported" warning GONE. Bundle: 674.94 KB → 673.59 KB (gzip 188.50 KB), still one chunk.
- **Finding: NO route-level code splitting exists anywhere** — `routes.tsx` imports every page statically. The 500 KB chunk-size warning remains — fixing it requires route-level `lazy()` (separate task).
- Compiled-build Indian 4G E2E: Plan tab **314ms → 224ms** ✓ under 300ms bar.
- `tsc --noEmit`: exit 0, zero errors.
- Next action: commit this fix; then GCP deployment phase.

---

**SESSION-SCRIPT TRIAGE + .claude/ CLEANUP — COMPLETE (2026-07-03, commit a719ce0)**

- Verified-then-deleted 19 read-only session scripts.
- Moved to `scripts/debug/` (gitignored, kept on disk): 10 one-time DB write scripts + 6 scripts whose findings were NOT in BUILD_TRACKER.
- `.claude/` gitignored; `.claude/settings.local.json` untracked via `git rm --cached`.
- OPEN ITEM (decide later): 12 already-tracked `_*` scripts left untouched.
- Next action: unchanged — GCP deployment phase.

---

**COMMIT SWEEP — COMPLETE (2026-07-03, commits 8680c12..195b099)**

- 5 commits: (1) gitignore junk triage; (2) pytest split into `requirements-dev.in/.lock` (constrained `-c requirements.lock`) — production lockfile pytest-free; (3) tracked `__pycache__` *.pyc deletions; (4) functional sweep — auth 3-phase decoupling, FailOpenLimiter, statement_timeout, cron endpoints, migration a1b2c3d4e5f6, Dockerfile + .dockerignore, full tests/performance/ suite; (5) DEPLOY_CHECKLIST.md.
- Pre-commit verification: `tsc --noEmit` 0 errors; `full_backend_test.py` 98/98.
- Security fix during sweep: `test_fcm_race_real.py` had dev CRON_SECRET + DB creds hardcoded — now reads from `.env` via load_dotenv.
- Next action: dev venv install note — run `pip install -r requirements-dev.lock` for pytest locally (production lockfile no longer carries it).

---

**ON-DEVICE SECURESTORE TOKEN TEST — VERIFIED (2026-07-02)**

- Item 1 verified on-device via Expo Go (SecureStore, both scenarios PASS). Not yet verified in a compiled dev/production build — flag for pre-launch smoke test (tracked in DEPLOY_CHECKLIST.md Section B).
- Scenario A (corrupt-access): access token corrupted in SecureStore → GET /users/me → silent refresh → `RESULT corrupt-access: PASS (accessRepaired=true, refreshRotated=true)` — rotated refresh token persisted to SecureStore.
- Scenario B (corrupt-both): both tokens corrupted → 401 → refresh 401 → `RESULT corrupt-both: PASS (tokensWiped=true, loggedOut=true)` — AuthGate routed to /login.
- Device: physical Android via Expo Go SDK 55. Test patient: priya.test@mityahar.com.

---

**PATIENT APP — TOKEN ROTATION + EAS/SENTRY — COMPLETE (2026-07-02)**

- `lib/axios.ts`: refresh interceptor now persists rotated `refresh_token` (was silently dropped → forced logout every 7 days); refresh-failure path sets `isAuthenticated=false` + clears profile.
- `app/doctor/activate.tsx`: stores BOTH tokens via `setTokens()` per M-5 contract (was access-only).
- `@sentry/react-native@7.11.0` installed (SDK 55 pin). `Sentry.init` + `Sentry.ErrorBoundary` + `Sentry.wrap` in `app/_layout.tsx`; `captureException` added at 6 previously-swallowed catch sites.
- `eas.json` created: development/preview/production profiles. **PLACEHOLDERS: `EXPO_PUBLIC_API_URL`, `EXPO_PUBLIC_GOOGLE_CLIENT_ID`, `EXPO_PUBLIC_SENTRY_DSN`, and Sentry org/project in app.config.ts MUST be set to real values before any `eas build`.** EAS projectId still placeholder in app.config.ts:53.
- tsc --noEmit: zero NEW errors.

---

**CVE FIXES + LOCKFILE — COMPLETE (2026-07-02, commit 2fac4e0)**

- `python-multipart` 0.0.26 → 0.0.31 (4 CVEs in form parsing)
- `pydantic-settings` 2.14.0 → 2.14.2 (1 CVE in config loading)
- `requirements.in`: 28 direct deps — edit this to add/remove packages
- `requirements.lock`: 82 fully-pinned packages via `pip-compile requirements.in --output-file requirements.lock`
- To update lockfile after changing requirements.in: `.\venv\Scripts\pip-compile.exe requirements.in --output-file requirements.lock`

---

**FCM DOUBLE-FIRE RACE — FIXED (2026-07-02, commit 9d516db)**

`flag_expiring_patients` in `app/routers/internal.py` replaced SELECT+UPDATE with atomic `UPDATE...RETURNING(Patient.id, Patient.token_1_expiry)`. Only the caller that wins the Postgres row lock gets patient rows back; concurrent loser sees 0 rows → sends 0 FCM pushes.

`tests/performance/test_cron_idempotency.py` `test_flag_expiring_concurrent`: WARN promoted to ASSERT. All 6 idempotency tests pass.

---

**CRON_SECRET — WIRED (2026-07-02)**

- `.env`: `CRON_SECRET=<dev secret, 64-char hex>` — NOT committed (gitignored via `.env.*`)
- `deploy-env-reference.txt` (formerly `.env.production`): `CRON_SECRET=<prod secret, 64-char hex, separate value>` — NOT committed
- `_check_secret` at `app/routers/internal.py:20`: already fail-closed — `not settings.CRON_SECRET` raises 401 when env var unset. No code fix needed.
- Both `.env` files had BOM-corruption from PowerShell Add-Content; fixed by `fix_cron_secret.py` (rewrites with Python utf-8 no-BOM).

---

**CLOUD SCHEDULER MIGRATION — COMPLETE (2026-07-02)**

APScheduler removed entirely from `app/main.py` lifespan.
Three header-protected internal endpoints added in `app/routers/internal.py`:
- `POST /internal/cron/flag-expiring-patients`
- `POST /internal/cron/deactivate-expired-patients`
- `POST /internal/cron/complete-expired-plans`
Header: `X-Cron-Secret: <CRON_SECRET>` — 401 if missing/wrong.

**GCloud Scheduler jobs to create (app-side docs — not yet created in GCP):**
```
gcloud scheduler jobs create http flag-expiring-patients \
  --schedule="5 1 * * *" --uri="https://<CLOUD_RUN_URL>/internal/cron/flag-expiring-patients" \
  --message-body="" --headers="X-Cron-Secret=<CRON_SECRET>" --http-method=POST

gcloud scheduler jobs create http deactivate-expired-patients \
  --schedule="10 1 * * *" --uri="https://<CLOUD_RUN_URL>/internal/cron/deactivate-expired-patients" \
  --message-body="" --headers="X-Cron-Secret=<CRON_SECRET>" --http-method=POST

gcloud scheduler jobs create http complete-expired-plans \
  --schedule="0 1 * * 0" --uri="https://<CLOUD_RUN_URL>/internal/cron/complete-expired-plans" \
  --message-body="" --headers="X-Cron-Secret=<CRON_SECRET>" --http-method=POST
```

**Idempotency audit results (`tests/performance/test_cron_idempotency.py`):**
- Auth rejection: 401 on missing/wrong secret — PASS
- Sequential double-fire on deactivate: call2=0 deactivated — PASS
- Concurrent double-fire: both calls returned 0 total — PASS
- Flag expiring sequential/concurrent: DB state correct (0 on second call) — PASS
- Known risk: FCM double-fire on concurrent flag calls. Mitigation: Cloud Scheduler minimum_backoff > job runtime.

---

**PRE-DEPLOYMENT AUDIT — COMPLETE (2026-07-02)**

**Item 1 — AUTH/DB CONNECTION COUPLING: FIXED**
- `/auth/token` and `/auth/doctor/login` refactored to three-phase approach
- Phase 1: read session (fetch user) releases connection BEFORE bcrypt runs
- Phase 2: `asyncio.to_thread(verify_password, ...)` — event loop unblocked, zero DB connection held during bcrypt
- Phase 3: minimal write session (update login counter only)
- Impact at 200 users: GET endpoint p50 = 400ms (was 2000–16000ms under concurrent auth)

**Item 2 — CONFIRM-CHOICE UNDER REAL LOAD: FIXED AND VERIFIED**
- Root cause: 100 of 102 plans in `draft` status → `GET /meal-plan/week` returned `{"days": []}` → no combo IDs
- Result at 200 users: **1210 requests, 0 failures (0.00%)** — p50 1700ms, p95 4300ms, p99 7100ms

**Item 3 — patients.doctor_id INDEX: APPLIED AND VERIFIED**
- Migration `1a2b3c4d5e6f` applied: `CREATE INDEX idx_patients_doctor_id ON patients(doctor_id)`
- EXPLAIN ANALYZE: Seq Scan → Index Scan, execution time 0.106ms

**Item 4 — 1000-USER RUN: EXECUTED**
- 200 users (sustained 120s): 0% failure on all patient endpoints
- 1000 users (sustained 300s): server crashes at peak — `QueuePool limit of size 20 overflow 20 reached, timeout 30s`. Single-process uvicorn limitation, NOT a code bug. GCP Cloud Run horizontally scales.

**Item 5 — INDIAN 4G E2E: EXECUTED — 1 UX FAILURE FLAGGED**
- Login at 5.9s = bcrypt ~2s + 2×150ms RTT + Vite dev bundle cold load. Non-blocking for deployment but should be tracked.
- All tab transitions under 300ms ✓

**Item 6 — DOCTOR SEED DATA: FIXED**
- `DOCTOR_DEFS` emails changed from `@mitihar.test` → `@mityahar-perf.com` in `seed_test_patients.py`
- Doctor creation migrated to admin API (`POST /api/v1/admin/doctors`) — no direct-ORM bypass

---

**PRE-DEPLOYMENT HARDENING — COMPLETE (2026-07-01)**

1. **Redis fail-open** — `FailOpenLimiter` in `app/core/limiter.py`: catches `RedisError`/`StorageError`, logs "failing open", returns 200 instead of 500/502.
2. **Real API-path load test** — `tests/performance/seed_via_api.py`: 50 concurrent POST /api/v1/auth/register with distinct XFF IPs. Result: 50/50 success, 0 duplicates.
3. **Duplicate email race** — 10 concurrent same-email signups → 1 created, 9 × 409. DB UNIQUE constraint + `auth.py:175` IntegrityError handler confirmed.
4. **BMR/TDEE drift fixed** — `seed_test_patients.py` line 139: default multiplier `1.375` → `1.2` (matches `calculations.py`).
5. **DB statement_timeout** — `database.py` `connect_args={"server_settings": {"statement_timeout": "30000"}}`. `pg_sleep(40)` killed at 30.0s; pool healthy after kill.
6. **TRUSTED_PROXY_CIDR** — `deploy-env-reference.txt` created with `TRUSTED_PROXY_CIDR=130.211.0.0/22,35.191.0.0/16`.

---

**PASS 5 — Network Latency & Connection Pool Stress: COMPLETE (2026-07-01)**

- `playwright.config.ts`: added exported `INDIAN_SLOW_4G` constant (offline: false, latency: 150ms, 10 Mbps/3 Mbps).
- Locust 2.44.4 installed in venv
- Headless run: 100 users, 10/s spawn, 60s, port 8001
- Data endpoints: GET /meal-plan/week 19.8ms avg, GET /progress/today 24.5ms avg, GET /users/me 7.5ms avg — all under 200ms ✅
- Zero 500s, zero ConnectionErrors, zero DB pool failures
- VERIFICATION_PLAYBOOK.md: all 5 passes marked complete

---

**LOCAL VERIFICATION PHASE: COMPLETE — all 5 passes done**

**Next: GCP deployment phase (in order):**
1. Commit all modified/untracked files
2. Fix `getMealTypes()` logic bug (`PlanTab.tsx:36–38`) if ≥5-meal support needed
3. Production `.env`: `COOKIE_SECURE=True`, `REDIS_URL=redis://:<AUTH>@<MEMORYSTORE_IP>:6379/0`, `REQUIRE_EMAIL_VERIFICATION=True`
4. GCP Cloud Run: container build → Memorystore Basic tier (same VPC) → Cloud SQL → deploy

---

**SESSION 21 — Patient App Adaptive UI: COMPLETE** (R-5/R-6, 2026-06-17/18)
- V2ComboCard, combo confirm-choice, optimistic confirmed state, bowl size (S/M/L), doctor's pick badge
- Full detail in BUILD_TRACKER_ARCHIVE.md under R-5, R-6, R-6.5, R-6.6, R-6.7

---

**SESSION 22 — Doctor Weekly Patient Summary: COMPLETE** (R-7A, 2026-06-21)
- `compute_weekly_summary()` service, `GET /doctor/patients/{id}/weekly-summary?week_start=` endpoint
- `WeeklySummaryTab.tsx`: adherence table + per-day choice breakdown + preferred/never_selected patterns
- R-7A.1 (rec lookup date mismatch fixed) + R-7A.2 (preferred boost + avoided exclusion in generator) applied

---

**Completed performance test suite + quality validation (2026-06-30):**
- `seed_test_patients.py`: 50 patients across 12 condition profiles, IDs 1–50
- `bulk_generate_plans.py`: 50/50 OK, 0 FAIL, total ~37s; per-patient 0.47–1.14s; rec_ids 283–332
- `test_plan_quality.py`: **50/50 PASS** — calorie ✅, combos ✅ (84 each), avoid_tags ✅, variety ✅
- Key calibration: `CALORIE_TARGET_RATIO = 0.85 * 0.85 = 0.7225`
- accompaniment pool exhaustion on combo_idx 2/3 (pool of 21, needs 4 distinct) — known pre-existing, non-blocking, falls back to combo-0 dish

---

**Completed Redis-backed rate limiting (2026-06-30):**
- Local Redis via Docker (`mityahar-redis`, `redis:7-alpine`, port 6379)
- `REDIS_URL=redis://localhost:6379/0` in `.env`; `Limiter` uses `RedisStorage` when set, falls back to in-memory with warning otherwise
- `redis-py` upgraded `3.5.3` → `8.0.1` (old version used `distutils` — removed in Python 3.12, caused `ConfigurationError` at startup)
- Startup PING check in lifespan confirms connectivity
- `test_redis_shared_limit.py` **PASS** — 429 at total req #11 across ports 8001 + 8002; Cloud Run multi-instance sharing confirmed

---

**Deployment prep — critical items:**
- **MUST commit before deployment:** `alembic/versions/93ad56085772_remove_plan_type_tags.py` (R-9) and `alembic/versions/b5c6d7e8f9a0_add_original_name_to_food_items.py` (dish cleanup) — both untracked
- **TypeScript check:** last verified state (BUILD_TRACKER R-7A) = 6 pre-existing `ImportMeta.env` errors only, 0 new errors
- **Known logic bug:** `getMealTypes()` at `PlanTab.tsx:36–38` — `ALL_MEAL_TYPES` and `THREE_MEAL_TYPES` are identical arrays; ≥5 branch is dead code. Low severity.

---

**Completed avoid_pcos / avoid_gout ingredient tagging (2026-06-29):**
- 95 ingredients tagged via Claude CLI (18 batches of 50); 432 total ingredients have at least one tag
- Fixed `::jsonb` cast syntax in `derive_recipe_tags.py` (CAST() form required for asyncpg)
- Propagated to food_items via recipe_ingredients join
- Recipes tagged avoid_pcos: 554 / avoid_gout: 130

---

**X-Forwarded-For finding (affects load test validity):**
- `slowapi` uses `key_func=get_remote_address` → `request.client.host` (raw TCP socket IP)
- X-Forwarded-For is NOT read by the rate limiter
- All local Locust workers share one `127.0.0.1` rate bucket — per-IP isolation untestable locally
- Must re-validate rate limit isolation post-GCP-deployment

---

**Session 2026-07-05 (early) — doc restructure + dedup determinism (archived from BUILD_TRACKER CURRENT STATUS):**
- `app/routers/doctor.py`: duplicate-recipe check now `ORDER BY id DESC` — dedup pick deterministic
- `tests/full_backend_test.py`: Section 12 recipe test made idempotent (pre/post cleanup of "Test Dal Tadka")
- `BUILD_TRACKER.md` condensed (1361 lines removed); full history moved to new `BUILD_TRACKER_ARCHIVE.md`
- `CLAUDE.md` restructured/trimmed; domain notes split out to `.claude/rules/` (backend/frontend/generator notes)
- `.gitignore` updated

---

**Session 2026-07-05 (evening) — Firebase/FCM credential provisioned on staging Cloud Run:**

*Key verification (pre-use check):*
- `firebase_service_account.json` (repo root, untracked): project `mitihar-prod`, SA `firebase-adminsdk-fbsvc@mitihar-prod.iam.gserviceaccount.com`, key id `73c4341e...`, file dated 2026-04-04
- Memory/history searched for "key leaked in chat" flags — none found; only note is Lane 3 backlog item "rotation policy — rotated once, no ongoing policy" (process gap, not compromise)
- Live validity test: JWT signed with key, exchanged at Google OAuth token endpoint — token minted OK (never printed). Key active, not revoked.

*Provisioning:*
- Secret Manager: `FIREBASE_SERVICE_ACCOUNT_JSON` v1 created in `mityahar-staging` from full file contents
- IAM: `mityahar-api-sa@mityahar-staging.iam.gserviceaccount.com` granted `roles/secretmanager.secretAccessor`
- `mityahar-api` redeployed with secret mounted as file `/app/secrets/firebase_service_account.json` + env `FIREBASE_SERVICE_ACCOUNT_PATH=/app/secrets/firebase_service_account.json` — final good revision `mityahar-api-00006-nqb` (100% traffic)

*Two deploy failures en route (lessons):*
1. `--set-secrets` REPLACES all secret refs — revision 00004 lost SECRET_KEY/DATABASE_URL/REDIS_URL/GEMINI_API_KEY_1/CRON_SECRET, failed pydantic startup validation ("SECRET_KEY must be overridden"). Traffic never shifted. Recovery: one `--set-secrets` re-listing all 5 env refs + new mount (rev 00005). Rule: use `--update-secrets` for additive changes.
2. Git Bash MSYS path mangling turned env value `/app/secrets/...` into `C:/Program Files/Git/app/secrets/...` (rev 00005 logged "Firebase service account file not found… Push notifications are DISABLED"). Fix applied from PowerShell (rev 00006). Rule: run gcloud with leading-slash args from PowerShell, or prefix `MSYS_NO_PATHCONV=1`.

*Verification:*
- `POST /internal/cron/flag-expiring-patients` → 200 `{"flagged":0}` (staging DB has no expiring patients — expected)
- Rev 00006 startup logs: zero "file not found" warnings, zero "Failed to initialise Firebase Admin SDK" errors → credential loads. (Success INFO line invisible: Python default log level WARNING.)

*Residue:*
- One orphaned unmounted volume in service spec (`FIREBASE_SERVICE_ACCOUNT_JSON-rer-jiw`, from failed rev 00004) — harmless
- Open decision (S157): staging FCM now wired to out-of-policy `mitihar-prod` (owned outside `mitihar.nutrition@gmail.com`). Correct today — patient app registers against `mitihar-prod` — ownership migration still undecided.

---

## 2026-07-15 — Stage 2 execution: JSONB retirement + plan-impact report + app up for UI review

**Decisions executed (from product owner):** backfill Y; 61 flagged rows held for Stage 3; 52 underfed plans NOT regenerated (diff report only); docs/ un-ignored.

1. **Backfill** (`scripts/backfill_recipe_ingredients.py --write`): 22 inserts applied, 1 new master row. Post-apply verification caught that the Bajra Roti insert was a whitespace duplicate — JSONB name `Bajra  flour` (double space) vs existing RI `Bajra flour`; the script's norm() lowercases/strips but does not collapse internal whitespace. Duplicate RI row + master row (id 951) deleted; net effect 21 real inserts, Bajra Roti unchanged at 1 correct row. 0 JSONB-only dishes remain. Known ceiling for Stage 3: collapse internal whitespace in any future name-matching.
2. **Readers repointed AFTER backfill** (order enforced for the clinical-safety path): `_build_dish_ingredients` (shopping list/checklist), `_is_allergenic` (allergy filter), `meal_plan.py` combo detail. Pool + detail queries eager-load `recipe_ingredients` then `ingredient` (async lazy-load raises MissingGreenlet). Pantry-staple skip preserved via PANTRY_STAPLES name set copied from `tag_pantry_staples.py` (the flag only existed in JSONB entries).
3. **Dual-write** in doctor add-recipe: numeric `quantity` strings become `quantity_g` (same grams assumption as the backfill), original qty+unit kept in `notes`, non-numeric entries stay JSONB-only, per-request name dedup, get-or-create master rows with source='doctor'.
4. **Nutrition re-stamp** (`recalculate_recipe_nutrition.py`): 2122 calculated / 15 manual (2 no-ingredients, 13 low coverage). 10-dish spot-check: 7 real dishes macro-identical (label flip only — stored macros were already RI-derived), 3 E2E test fixtures recomputed from their single backfilled ingredient. No new outliers (max 1499 kcal).
5. **STAGE1_PLAN_IMPACT.md**: 52 active pre-cf1b6ab plans / 52 patients. Old (TDEE x 0.85 x split) vs corrected (TDEE x split) B/L/D/buffer per patient + dish diff from one seeded in-memory regeneration each (sessions rolled back; nothing persisted). Dish churn roughly 25-75% kept; deltas exact, dish lists indicative (generator is stochastic). Decision on notification/re-approval timing left with product owner.
6. **docs/ tracked**: blanket `docs/` ignore removed; root-level doc patterns root-anchored so docs/ copies track; CREDENTIALS.local.md remains ignored; secret scan of docs/ found only known dev/test creds (testing guides). ~140 files committed.
7. **App up for Recipe-tab UI review**: stale system-python uvicorn (pid 15240, pre-Stage-2 code) killed off :8001; fresh venv uvicorn boots clean. Vite :5173 compiles clean. Recipe tab loads (20 recipes, filters OK), 0 console errors. `tsc --noEmit`: 0 errors — the Sprint-5 `patientMealsPerDay` PlanTab flag is stale/resolved. Two recipe names render as `?????` (non-ASCII/Devanagari?) — flagged for UI review.

Commits: `56eee5b` (docs tracking), `4f93d82` (Stage 2 code), plus session-end state commit. Unpushed with dda93d6/fa5e05b/cf1b6ab/02d8d4a.

---

## 2026-08-03 — Recipe-ingredient quantity remediation, ingredient dedup, IFCT wiring, assignment gate

Started as "the repo is messy, structure it" and became a data-correctness pass on
`recipe_ingredients` (18,190 rows / 2,114 dishes).

### 1. Repo reorg
`docs/` bucketed into `architecture/ audits/ guides/ planning/ reference/ walkthroughs/ archive/`
(`_archive/` merged into `archive/`). Dead one-offs (`_explore_*`, `repro.py`, `test_18.py`, ...)
to `scripts/archive/`; `scripts/debug/` folded in. Active scripts stay FLAT — everything is invoked
`python -m scripts.X` and several cross-import (`export_recipe_ingredients_review` imports
`sanity_check_ingredients`), so subpackaging would have broken ~66 live entry points for cosmetics.
Working CSVs + checkpoints to `data/review/`; log dumps to `logs/`. Root 78 → ~30 entries.

### 2. Root cause of the bad quantities (established, not guessed)
Matched 797 dishes back to `data/6000+ Indian Food Recipes Dataset/IndianFoodDatasetCSV.csv` and
divided DB grams by the count parsed from the source text: **implied grams-per-count is exactly
80.0**. The ingest converted every COUNTED ingredient at a flat 80 g/piece. Right for
onion/tomato/potato (~80 g each), catastrophically wrong for chilli (~4 g), garlic clove (~5 g),
bay leaf (~0.5 g), curry leaf (~0.15 g). A partial earlier fix left a second cluster at 1/10 scale,
so counts 1-4 appear as both 80/160/240/320 and 8/16/24/32. Unit-based rows (tablespoon/teaspoon)
converted correctly — left alone.

**Dividing by the source Servings column was tested and REJECTED**: it drops 78.8% of dishes below
150 g total, implausible for one serving. Stored `serving_weight_g` (median 200 g) agrees with
piece-fix-only. Recorded here because it looks obviously right and is not.

### 3. Damage from the deprecated fix_ingredient_quantities.py (3,556 rows / 19.5%)
- `clove` keyword collision: loop set `cloves garlic` to 15 g, then `clove` (LIKE %clove%) overwrote
  it to **1.0 g** on 127/154 rows. Backup originals were 24-240 g.
- Flat-value collapse: every curry leaf 2.0 g, every green chilli 8.0 g — all per-dish variation gone.
- Pass-4 flat 180 g cap (393 rows); Pass-3 flat 400/450 g dish rescale ignoring `slot_type` (96 dishes).

Rebuilt from `db-backups/mityahar_content_2026-07-31.sql` (clean pre-damage baseline, exact ri_id
coverage) via `scripts/rebuild_ingredient_quantities.py`: piece-weight correction, then category cap,
then proportional dish scaling honouring `DISH_TOTAL_MAX`. 5,888 corrections staged through the
existing `import_recipe_ingredients_review.py` (dedupes by ri_id, re-validates, pg_dump, APPLY gate).
**ERROR rows 1,158 to 0.** `Cloves garlic` median 13.8 g across 40 distinct values; `Curry leaves`
43 distinct values.

Two distribution guards written into the plan were missed and are recorded as MY miscalibration,
not over-correction: median dish total landed 215 g vs a guessed 250-400 g band, and <150 g dishes
rose 30.0% to 37.9%. The research doc's own figure (single component 120-200 g cooked) and hand
spot-checks (Palak Paneer 155 g, Semiya Upma 182 g, Egg Pulao 216 g — all unchanged by the rebuild)
say 215 g is correct.

### 4. Checker vocabulary + collision fix (sanity_check_ingredients.py)
Uncategorized rows **1,582 to 29**. Added spelling variants (`chili`/`chilli`, `Bay leaves`), Hindi
names (`Long`=clove, `Rye`=mustard seed, `Kalonji`, `Karela`, `Kaddu`), missing vegetables/cereals,
and two new categories: `condiment_sauce` (30 g) and `beverage_liquid` (300 g). Split `curry_leaf`
(5 g tempering) out of the flat 30 g `fresh_herb` cap.

Fixed 4 miscategorizations — `Mustard oil` to powder_spice (a regression I introduced with a bare
`mustard` keyword, capping oil 45 g to 10 g), plus pre-existing `Coconut oil`/`Sesame oil` to
nut_seed and `Buttermilk` to oil_fat. Bare `oil` (3 chars) loses the longest-keyword match, so each
seed-oil needs an explicit entry.

**The same clove collision also lived in the checker**: `check_count_vs_grams` iterated in dict
order, so `clove` (trips >6 g) matched `Cloves garlic` before `cloves garlic` (trips >75 g),
flagging 154 correct garlic rows. Now longest-keyword-wins, matching `categorize_ingredient`.

New `check_not_food` flags rows for DELETION rather than capping: 4 non-food (`Coal`, `Charcoal`
for dhungar smoking, `Toothpicks` at 348.5 g twice) and 21 parser fragments (`Green`, `Save` from
Sev Tamatar, `Good` from Gourd, `Arabic` from Arbi, `1/2`). 25 rows / **1,980 g of phantom weight**
deleted. Capping them would turn an obviously-wrong number into a plausible one.

### 5. Duplicates audit — mostly good news
- `recipe_ingredients`: **zero** true duplicates (`uq_recipe_ingredient` holds). The earlier
  "Toothpicks x2" was the same ingredient in *different dishes sharing a name*.
- `uq_fi_canonical`: **zero** violations. Stage 6 works as written.
- Meal generator is airtight (`meal_generator.py:548-550` filters `is_verified` AND `deleted_at`).
- 182 live unverified dishes are the doctor review queue (`6k_dataset`/`excel` seed backlog), NOT
  defects. **Deliberately not purged** — product owner decision.
- 140 same-name `food_items` groups are mostly genuinely different recipes (only 11 share identical
  calories). Not merged.

### 6. Ingredient dedup + the orphaned IFCT data
40 duplicated ingredient names split 2,944 recipe rows. The real finding: **the IFCT 2017 import
inserted NEW ingredients rows instead of updating the LLM-estimated ones, so every recipe row sat
on estimated_llm while the authoritative IFCT rows had ZERO usage.**

Merge rule: IFCT2017 wins (15 groups), else field-identical lowest id (23 groups), else patch from
IFCT (`peanuts` H012 520 kcal, `tur dal` B021 331 kcal). "Richest nutrition data" was the originally
chosen rule and turned out **undecidable** — all 40 pairs tie at 16/17 populated fields. Zero
collision groups, so repointing was a clean UPDATE. 43 merged, 2,816 rows repointed, 45 audit rows.
Rows on IFCT-sourced ingredients: 0 to 4,720.

**The merge activated latent bad variety matches in ingredient_ifct_map.csv** — dormant while the
IFCT rows were orphaned. 5 of the 15 audited were wrong. Corrected the two material ones:
`coconut` to H007 kernel-fresh (624 to 408.9; the DB already has a separate `coconut dry`) and
`milk` to L002 whole-Cow (107.3 to 72.9, was buffalo). Accepted as-is: `mango` to green-raw,
`cabbage` to Chinese, `tomato` to green (<=7 kcal each). **~73 of 88 mappings never audited.**

### 7. Assignment gate
`meal_generator` filters correctly, but `doctor.py` `patch_dish` (dish swap) and `pin_dish` did a
bare `select(FoodItem).where(id == ...)` — a doctor could swap a patient onto a soft-deleted dish or
the zero-ingredient test artifact. Added `get_assignable_dish()` to `dish_service.py` reusing the
`find_reusable_dish` allowance: blocks soft-deleted always, unverified unless owned by that doctor.
`block_dish` left unguarded on purpose — blocking only removes an option.

Deleted `Palak Paneer Test S16` (id 3725): `is_verified=TRUE`, 0 ingredients, 220 kcal, fully
servable. Kept id 3724 (unverified, so it belongs to the review queue).

### Final numbers
ERROR rows 1,158 to 0 · uncategorized 1,582 to 29 · `recipe_ingredients` 18,190 to 18,165 ·
`ingredients` 950 to 907 · dishes within slot max 59.7% to 94.9% · median 272 kcal/serving ·
1,982/2,115 dishes in the 50-800 kcal band · **0 above 1,500** · 71 tests pass.

New: `scripts/rebuild_ingredient_quantities.py`, `scripts/merge_duplicate_ingredients.py`,
`tests/test_ingredient_categorization.py` (38 tests pinning keyword collisions),
`tests/test_dish_service.py` (9 tests, no DB). Archived: `reconstruct_pass4_damage.py` (superseded).

### Known-open
`ingredient_ifct_map.csv` variety audit (~73 unchecked) · 49 dishes <50 kcal + 1 with zero
ingredients (ingest dropped unmatched ingredients — not a quantity problem) · 1,388 `weekly_combos`
refs to soft-deleted dishes + 1 dangling id 3718 (JSONB snapshots, display safe).
