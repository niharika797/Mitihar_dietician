# Sprint 5 Handoff — Mitihar
_Last updated: March 28, 2026_

---

## What Was Done This Session

### Bug Fixes (Patient App)

#### BF-1 — ExpoKeepAwake Android Error (Suppressed)
- **File:** `mitihar-patient-app/app/_layout.tsx`
- Added `LogBox.ignoreLogs(["ExpoKeepAwake.activate", "The current activity is no longer available"])`
  gated behind `__DEV__` to silence the dev-mode-only Android lifecycle noise.
- Not a real bug — caused by expo-router internals, not app code.

#### BF-2 — Onboarding Submission Timeout ("Something went wrong")
- **Root cause:** `POST /patients/onboarding` was synchronously generating the diet plan
  inside the HTTP request handler. Plan generation is CPU-intensive and exceeded the 15s
  axios timeout. Metro showed nothing because it was a client-side timeout, not a crash.
- **Fix — Backend:** `app/routers/patients.py`
  - Extracted plan generation into `_generate_plan_background()` coroutine
  - Uses its own `AsyncSessionLocal` session (not the request-scoped one)
  - Registered via `background_tasks.add_task()` — returns 200 immediately, plan generates after
- **Fix — Frontend:** `mitihar-patient-app/lib/axios.ts` — timeout raised from 15s → 30s
- **Fix — Frontend:** `mitihar-patient-app/app/(onboarding)/complete.tsx`
  - Removed `generatePlan()` call from `useEffect` (plan already exists from onboarding endpoint)
  - Removed `planReady` state + spinner gate — CTA button is immediately tappable
  - Replaced with `qc.invalidateQueries(QUERY_KEYS.WEEK_PLAN)` so Meals tab refetches fresh

#### BF-3 — getApiError Hid JS Errors
- **File:** `mitihar-patient-app/lib/getApiError.ts`
- Added early return for plain `Error` instances (no `.response` property) so `toPayload()`
  validation errors show their actual message instead of the generic fallback.

#### BF-4 — IP Address Change (Network Error)
- `.env` `EXPO_PUBLIC_API_URL` updated from `192.168.0.101` → `192.168.0.100`
- **Note for future:** Router assigns IPs dynamically via DHCP. Assign the PC a static local
  IP in router settings to prevent this recurring. Metro's URL always shows the current IP.

#### BF-5 — Wrong Gemini Model (Retired)
- Old scripts were using `gemini-2.0-flash-lite` which was deprecated March 2026.
- All references updated to `gemini-2.5-flash-lite`.

---

### Doctor Dashboard Features

#### F-1 — Meals Per Day Consistency (Task 1)
- **Files:** `mitihar-frontend/apps/src/app/pages/doctor/PatientDetail.tsx`
  and `patient-tabs/PlanTab.tsx`
- `patientMealsPerDay` prop added to `PlanTab`
- 3-meal plan → shows only Breakfast, Lunch, Dinner
- 5-meal plan → shows all 5 slots (including MorningSnacks, EveningSnacks)
- TDEE bar label now shows "(3-meal plan)" or "(5-meal plan)" for context
- "Add Custom Meal" Meal Type dropdown also filters to patient's allowed slots

#### F-2 — Auto-Submit to Global Dataset (Task 2)
- **File:** `patient-tabs/PlanTab.tsx`
- Removed both checkboxes ("Save to library" + "Submit to global dataset") from Add Meal form
- `submit_to_global: true` now hardcoded on every `addRecipe()` call
- Replaced with a static info note: "This meal will be saved to your library and submitted
  to the global dataset for admin review"

#### F-3 — Inline Meal Edit (Task 3)
- **File:** `patient-tabs/PlanTab.tsx` — `MealCard` component
- "Edit meal" option added to `···` menu on each meal card
- Opens inline edit form pre-filled with current dish name + all macro fields
- On save, calls `doctorApi.overridePlan()` with the full updated meals array
  (only the edited meal is swapped, rest unchanged)
- Note: edited meal is NOT separately re-submitted to recipe library on edit —
  only new meals via "Add Custom Meal" go to library

#### F-4 — Dish Name Autocomplete + Gemini Nutrition Lookup (Task 4)
- **Frontend:** `patient-tabs/PlanTab.tsx`
  - Dish name input replaced with debounced search (300ms) querying `browseRecipes(search)`
  - Dropdown shows matching dishes from DB; selecting one fills all macro fields
  - "AI Lookup" button (Sparkles icon) calls backend Gemini endpoint
  - Results are editable before saving
- **Backend:** `app/routers/doctor.py` — new endpoint at end of file:
  ```
  POST /api/v1/doctor/recipes/lookup
  Body: { "food_name": string }
  Returns: { food_name, calories, protein, carbs, fat, fiber, source: "gemini_estimate" }
  ```
  - Uses `GEMINI_API_KEY_1` (single key — all 4 keys share same project quota, rotation useless)
  - Model: `gemini-2.5-flash-lite`
  - Strips markdown fences from Gemini response before JSON parse
  - Returns 503 if no key configured, 502 on Gemini error

---

### Dish Name Cleanup — Batch Script (Task 5)

- **File:** `scripts/rename_dishes_gemini.py`
- One-time job to rename all `food_items.recipe_name` to simple Indian names
- Uses Gemini 2.5 Flash-Lite free tier — **zero billing risk** as long as no billing
  account is linked to the Google Cloud project

**Key design decisions:**
- Single API key only (not rotating — quota is per project not per key)
- Batch size: 20 dishes per call
- Delay: 5s between batches (~12 RPM, safely under 15 RPM free cap)
- On 429: reads `Retry-After` header, waits, retries up to 3× then exits cleanly
- Daily cap hit → `sys.exit(0)` with checkpoint saved (not a crash)
- Checkpoint file: `rename_checkpoint.json` — stores all processed food IDs
- Backup file: `rename_dishes_backup.json` — original names saved before first run
- Idempotent: safe to re-run any number of times

**Current status (as of March 28, 2026):**
- 2137 total dishes in DB
- ~440 processed (22 batches completed across 2 runs)
- ~1697 remaining (~85 batches, ~4 more daily runs)
- Checkpoint file exists and is valid

**To continue:**
```cmd
cd C:\Users\Lenovo\Desktop\Code\2026\Nutria\Mitihar_dietician
venv\Scripts\python -m scripts.rename_dishes_gemini
```

**To preview without writing:**
```cmd
venv\Scripts\python -m scripts.rename_dishes_gemini --dry-run
```

---

## Pending / Known Issues

### P-1 — Frontend Compilation Not Verified
Tasks 1–4 (PlanTab.tsx rewrite) were written directly to disk. The frontend has not been
started and compiled since these changes. First thing in the next session:
```cmd
cd mitihar-frontend/apps
pnpm dev
```
Check browser console for TypeScript errors, especially around `patientMealsPerDay` prop
and the new autocomplete imports.

### P-2 — Backend recipes/lookup Not Integration-Tested
The new Gemini lookup endpoint was added to `doctor.py` but not tested with a live call.
Restart uvicorn and test manually:
```bash
curl -X POST http://localhost:8000/api/v1/doctor/recipes/lookup \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"food_name": "Aloo Paratha"}'
```
Expected: JSON with calories/protein/carbs/fat/fiber fields.

### P-3 — Dish Rename Script Still Running
Not a code issue — just needs to be run once per day for ~4 more days until all 2137
dishes are processed. See Task 5 section above.

---

## Architecture Notes (Important for Next Session)

### Gemini API Keys
- 4 keys in `.env`: `GEMINI_API_KEY_1` through `GEMINI_API_KEY_4`
- **All 4 share the same Google Cloud project quota** — rotating them gives zero extra RPM/RPD
- For the rename script: uses `GEMINI_API_KEY_1` only (first key found in env)
- For the real-time lookup endpoint: uses `GEMINI_API_KEY_1` only
- Free tier limits: 15 RPM, ~1500 RPD (per project)
- Model to use: `gemini-2.5-flash-lite` (2.0 models are retired as of March 2026)

### IP Address
- Backend runs locally on the dev machine, NOT in Docker
- Docker only runs PostgreSQL (`mityahar_postgres` container)
- Patient app `.env` `EXPO_PUBLIC_API_URL` must match the machine's current local IP
- Current: `http://192.168.0.100:8000/api/v1`
- If "Network error" appears again, check Metro's URL line — that IP is the current one

### Backend Start Command
```cmd
cd C:\Users\Lenovo\Desktop\Code\2026\Nutria\Mitihar_dietician
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Patient App Start Command
```cmd
cd C:\Users\Lenovo\Desktop\Code\2026\Nutria\Mitihar_dietician\mitihar-patient-app
npx expo start --clear
```

---

## Deferred Tasks (Not Started)

| # | Task | Notes |
|---|---|---|
| D-1 | Doctor adds extra meal slot beyond patient's meals_per_day | Very optional, complex |
| D-2 | Firebase push notifications setup | Needs Firebase project + Google account |
| D-3 | Google OAuth / 2FA for doctor dashboard | Pending Firebase setup |
| D-4 | Production deployment to Google Cloud | After all features stable |
| D-5 | Razorpay billing integration | Needs Razorpay account + KYC first |

---

## Files Changed This Session

### Backend
| File | Change |
|---|---|
| `app/routers/patients.py` | Background task for plan generation; added `BackgroundTasks` param |
| `app/routers/doctor.py` | New `POST /doctor/recipes/lookup` endpoint + `_generate_plan_background` helper |
| `scripts/rename_dishes_gemini.py` | Full rewrite — correct model, single key, checkpoint, retry logic |

### Patient App
| File | Change |
|---|---|
| `app/_layout.tsx` | LogBox suppress for ExpoKeepAwake; import LogBox from react-native |
| `app/(onboarding)/complete.tsx` | Removed generatePlan call; CTA immediately tappable |
| `app/(onboarding)/disclaimer.tsx` | Wrapped toPayload() in try/catch for better error messages |
| `lib/axios.ts` | Timeout 15s → 30s |
| `lib/getApiError.ts` | Handle plain Error instances (no .response) |
| `.env` | IP updated 192.168.0.101 → 192.168.0.100 |

### Doctor Dashboard
| File | Change |
|---|---|
| `src/app/pages/doctor/PatientDetail.tsx` | Pass `patientMealsPerDay` prop to PlanTab |
| `src/app/pages/doctor/patient-tabs/PlanTab.tsx` | Full rewrite — Tasks 1, 2, 3, 4 |
