# Mityahar — Build Tracker

**Last updated:** 2026-07-05 (first staging deploy — GCP infra + Cloud Run live)  
**Rate limiter:** Redis-backed via slowapi RedisStorage; multi-instance sharing verified locally; staging Memorystore `mityahar-redis` provisioned (AUTH enabled).  
**Maintained by:** Claude Code — THIS file only (not the archive) is read at session start. Update CURRENT STATUS below at session end; append full session narrative to BUILD_TRACKER_ARCHIVE.md.

---

## HOW TO USE THIS FILE

1. **Every session starts here.** Read this file completely before touching any code.
2. **Never guess at prior decisions.** If something seems wrong or contradicts this file, ping the product owner before proceeding.
3. **Cross-reference:** Full audit reports in `docs/`. Full session history in `BUILD_TRACKER_ARCHIVE.md` (open on demand, not at session start).
4. **Session end:** Overwrite `CURRENT_STATE.md` (max 20 lines, no history). Append full narrative to `BUILD_TRACKER_ARCHIVE.md`. Update CURRENT STATUS below (max 40 lines).

---

## PLATFORM OVERVIEW

**Three services:**
- Backend: FastAPI → `localhost:8001` (project root)
- Doctor Dashboard: React + Vite → `localhost:5173` (`mitihar-frontend/apps/`)
- Patient App: Expo Web → `localhost:8081` (`mitihar-patient-app/`)

**Project root:** `C:\Users\Lenovo\Desktop\Code\2026\Nutria\Mitihar_dietician`  
**DB:** `postgresql+asyncpg://admin:mityahar_dev@localhost:5432/mityahar_db`  
**Credentials:** see `docs/CREDENTIALS.local.md` (gitignored — not in repo)

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
| full_backend_test.py crashed before reaching admin login (port 8000 vs 8001, no error handling) | ~~P1~~ FIXED | 2026-06-30 — port corrected, health check try/except added, sys.exit(1) on backend-down; gdpr_consent added to Section 8 registration payload; hdr() guarded against empty token; serving_weight_g added + plan_type_tags removed from Section 12 recipe payload. 94/94 passing across 16 sections. |
| confirm-choice accepts any food_item_id regardless of whether its meal_time_tags match the requested meal_type — a Breakfast dish can be confirmed into a Lunch slot via direct API call. Fix: add `meal_time_tags @> ARRAY[meal_type_lower]` validation in the endpoint before the upsert. Deferred — low risk since the suggestions endpoint only surfaces slot-appropriate dishes to patients. | P2 | Session 20 |

---

## CURRENT STATUS

> _Updated 2026-08-05. Max 40 lines. Full narrative in BUILD_TRACKER_ARCHIVE.md._

**Committed (`0a2cfbe`):** Quantity-aware pantry backend + grams input UI — `patient_pantry.quantity_g` three-state, migration `e4f5a6b7c8d9`, `_PANTRY_IN_STOCK` predicate, live-computed `/shopping-list`, `confirm-choice` pantry deltas, debounced grams input in `PantrySection`.

**Phase:** Staging deployed — first successful Cloud Run deploy 2026-07-05. Prior "Done" block archived to BUILD_TRACKER_ARCHIVE.md.

**Done (2026-07-05):**
- GCP staging infra built (project `mityahar-staging`, region `asia-south1`):
  - VPC `mityahar-vpc` / subnet `mityahar-subnet`; Cloud Run uses **Direct VPC Egress** (no serverless VPC connector)
  - Cloud SQL `mityahar-pg` (PostgreSQL, `db-custom-2-7680`), **private IP only** — no public IP
  - Memorystore Redis `mityahar-redis`, AUTH enabled; transit encryption DISABLED (default, never reviewed — unencrypted in transit within VPC; formal review pending before production)
  - Artifact Registry image (`asia-south1-docker.pkg.dev/.../mityahar-api`)
  - Service accounts: `mityahar-api-sa` (runtime), `mityahar-scheduler-sa` (Cloud Scheduler invoker)
- 5 Secret Manager secrets wired to the service: SECRET_KEY, CRON_SECRET, GEMINI_API_KEY_1, DATABASE_URL, REDIS_URL.
  GOOGLE_CLIENT_SECRET explicitly excluded — confirmed unused by any code path.
- First deploy live: https://mityahar-api-759811872653.asia-south1.run.app
  Revision env verified: `ENVIRONMENT=staging`, `COOKIE_SECURE=True`, CORS = Firebase hosting origins, TRUSTED_PROXY_CIDR set.
- Alembic: **34/34 migrations applied** to staging via Cloud Run job `mityahar-migrate` (execution `mityahar-migrate-8bcs2`).
  Local cloud-sql-proxy CANNOT reach the instance (private IP only) — do not retry proxy path.
- Discovery: `GOOGLE_CLIENT_SECRET` / `GOOGLE_REDIRECT_URI` are dead config — never read by app code.
- Confirmed APScheduler fully removed (zero refs in `app/`); cron = 3 `/internal/cron/*` endpoints guarded by CRON_SECRET.
- **2026-07-13:** Found + fixed job-digest drift — `mityahar-migrate`/`mityahar-seed-runner` were pinned to a 2026-07-05 image predating a `scripts/` COPY fix; every later service redeploy silently left the jobs stale. Redeployed service (`mityahar-api-00008-jjn`), repointed both jobs, verified `scripts/` present. Added `scripts/deploy_staging.py` so deploy always repoints pinned jobs — don't reuse bare `gcloud run deploy` for this service.
- **2026-07-14:** 2 test fixes committed — correct JSONB key names in plan-quality avoid-tag/variety checks (`dda93d6`), add env-var overrides for staging-targeted perf tests (`fa5e05b`).
- **2026-07-15:** Fixed double-applied 15% TDEE buffer in meal generator (`cf1b6ab`) — meals were landing at 72.25% of TDEE, not 85%; unit tests added. Ran the read-only stage-2 nutrition-source migration diff (`02d8d4a`): JSONB vs `recipe_ingredients` conflicts confirmed as stale 10x values, gated dry-run `backfill_recipe_ingredients.py` added (22-row scope); flagged `meal_generator._is_allergenic` as still reading legacy JSONB. Added `scripts/export_recipes_to_csv.py`, ran it to produce `recipe_ingredients_audit.csv` (18,213 rows, uncommitted).
- **2026-07-28:** Committed the Stage 6 spec doc (`254d110`, sections 1-4) that was missing from the repo. Added `DataChangeRequest` model (`56fd3ea`, Section 1 task 1) — pending/approved/rejected/auto_applied lifecycle for Tier 1 auto-merge, Tier 2 AI research, doctor flags. Re-ran the full backend integration suite after the model change: 94/94 steps + 10/10 error cases PASS (`tests/results/test_results_latest.txt`, untracked).
- **2026-07-29:** Live read-only audit of the running app (`docs/AUDIT_SESSION_2026-07-29.md`) — found the patient Expo web app broken (Router/Navigation mismatch), a weight-loss calorie-deficit gap, beverage-dominated accompaniment slots, 292 duplicate dish names, and ingredient nutrition only 9% real IFCT2017 (79% LLM-estimated, mineral tables never imported). Corrected stale avoid-tag claims in `.claude/rules/generator-notes.md`. `scripts/extract_ifct_tables.py`: extracted + verified Tables 1-7 (proximates/vitamins/carotenoids/minerals/starches/fatty-acids), all 0-mismatch; per product-owner call, stopped there — Tables 8-12 and ingredient images aren't needed by the platform.
- **2026-07-30:** Wired the `tags_locked` doctor-override guard into `PATCH /doctor/recipes/{id}/tags` (`app/routers/doctor.py`) — doctor tag edits now set `tags_locked=True` so `derive_medical_tags.py` will skip locked rows.
- **2026-07-30 (later same day):** Bumped `mitihar-patient-app` deps (`package.json`/`pnpm-lock.yaml`): `expo` 55.0.27→55.0.28 (+ expo-* patch bumps), `@react-navigation/native` 7.1.28→7.3.14, `react-native` 0.83.6→0.83.10. Uncommitted.
- **2026-07-30 (later still):** Built pantry-first meal planning end-to-end, uncommitted: `PatientPantry` model + migration `c1d2e3f4a5b6` (not yet run); `meal_generator.is_staple()` substring staple-check; `meal_plan.py` router gets `GET/POST /pantry` and `GET /pantry/suggestions` (condition-aware, IFCT iron/calcium/fiber cols), `GET /week` now scores + sorts combos by pantry coverage (have/required/missing/cookable). Mobile: new `meals/pantry.tsx` screen + nav entry, types/service/queryKeys wired, `meals.tsx` tab shows "Cook now"/coverage badge and "My Pantry" button.

**Blockers / pending:**
- New pending-visit approve/reject flow not yet verified end-to-end in a running app.
- `infra/cloud_scheduler_jobs.sh` not yet executed — the 3 cron endpoints remain unscheduled in GCP.
- Pantry endpoints/UI (prior session) still unverified against a running app.

**Next action:**
Run the app and walk the flag → approve/reject loop end-to-end, then run `infra/cloud_scheduler_jobs.sh` against staging (needs `CRON_SECRET` from Secret Manager).

**Standing constraint:** COOKIE_SECURE fail-closed guard only fires when `ENVIRONMENT=production`. Every non-production tier must set `COOKIE_SECURE=True` explicitly (staging does).
