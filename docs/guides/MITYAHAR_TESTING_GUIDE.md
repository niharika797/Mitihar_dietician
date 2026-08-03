# Mityahar API — Manual Testing Guide

---

## Setup

### Start the Server
```
cd C:\Users\Lenovo\Desktop\Code\2026\Nutria\Mitihar_dietician
venv\Scripts\activate
venv\Scripts\uvicorn app.main:app --reload --port 8001
```

### Postman / Insomnia Configuration
1. **Base URL:** `http://localhost:8001/api/v1`
2. **Default Header:** `Content-Type: application/json` for all JSON body requests.
3. **Form-encoded requests:** Change body type to `x-www-form-urlencoded` for all login endpoints (they use `username` and `password` fields, not JSON).
4. **Bearer token:** For every protected endpoint, add an `Authorization` header with the value `Bearer <token>`. In Postman, use the **Authorization tab → Bearer Token** field. In Insomnia, use **Auth → Bearer Token**.
5. **Swagger UI (optional reference):** `http://localhost:8001/docs`

---

## Variables to Track

Save these values as you progress through the test phases. Reference them by name in each step.

| Variable | Where to Get It | Used In |
|---|---|---|
| `admin_token` | Step 1 — Admin Login | All `/admin/*` requests |
| `doctor_id` | Step 7 — Create Doctor | Steps 9–11, 13, 68–84 |
| `doctor_token` | Step 5 — Doctor Login | All `/doctor/*` requests |
| `patient_token` | Step 3 — Patient Login | All `/patients/*`, `/diet-plans/*`, `/meal-plan/*`, `/progress/*` |
| `patient_id` | Step 3 response or Step 23 (GET /users/me) | Steps 15, 22, 68–75, 84 |
| `refresh_token` | Step 3 — Patient Login | Step 4 |
| `code` | Step 13 or Step 79 | Step 27 |
| `request_id` | Step 28 — Request Doctor Connection | Steps 77–78 |
| `recommendation_id` | Step 35 — GET /diet-plans/my-plan | Step 47, Step 65 |
| `log_id` | Step 46 — Log a Meal | Steps 48–49 |
| `recipe_id` | Step 82 — Add Custom Recipe | Step 83 |
| `food_id` | Step 16 — List Food Items | Steps 17–19 |

---

## Phase 1 — Admin Setup

> **Goal:** Log in as admin, then create a doctor account. Everything else depends on these two steps.

---

### Step 1: Admin Login

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `http://localhost:8001/api/v1/auth/admin/login` |
| Auth | None |
| Body type | `x-www-form-urlencoded` |

**Body fields:**
```
username = admin@mityahar.com
password = Admin@1234
```

**Verify:**
- Status: `200 OK`
- Response contains `access_token` and `token_type: "bearer"`

**Save:** Copy `access_token` → store as **`admin_token`**

---

### Step 2: Create Doctor

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `http://localhost:8001/api/v1/admin/doctors` |
| Auth | Bearer `admin_token` |
| Body type | JSON |

**Body:**
```json
{
  "email": "drpriya@mityahar.com",
  "password": "Doctor@1234",
  "name": "Dr. Priya Mehta",
  "phone": "9876543210",
  "specialization": "Dietitian",
  "clinic_name": "Healthy Roots Clinic",
  "city": "Mumbai"
}
```

**Verify:**
- Status: `201 Created`
- Response contains `id`, `email`, `name`, `is_active: true`
- Calling again with the same email returns `409 Conflict`

**Save:** Copy `id` from response → store as **`doctor_id`**

---

## Phase 2 — Patient Registration & Onboarding

> **Goal:** Register a patient, log in, complete onboarding. Onboarding auto-generates the first diet plan.

---

### Step 3: Patient Register

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `http://localhost:8001/api/v1/auth/register` |
| Auth | None |
| Body type | JSON |

**Body:**
```json
{
  "email": "testpatient@gmail.com",
  "password": "Patient@123",
  "name": "Rahul Sharma",
  "age": 28,
  "gender": "Male",
  "height": 175,
  "weight": 72,
  "activity_level": "MA",
  "diet": "Vegetarian",
  "health_condition": "Healthy",
  "region": "North"
}
```

**Verify:**
- Status: `201 Created`
- Response contains patient profile with `id`, `email`, `subscription_status: "inactive"`

**Save:** Note `id` from response → store as **`patient_id`**

---

### Step 4: Patient Login

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `http://localhost:8001/api/v1/auth/token` |
| Auth | None |
| Body type | `x-www-form-urlencoded` |

**Body fields:**
```
username = testpatient@gmail.com
password = Patient@123
```

**Verify:**
- Status: `200 OK`
- Response contains `access_token`, `refresh_token`, `token_type: "bearer"`

**Save:** Copy `access_token` → **`patient_token`**; copy `refresh_token` → **`refresh_token`**

---

### Step 5: Refresh Token

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `http://localhost:8001/api/v1/auth/refresh` |
| Auth | None |
| Body type | JSON |

**Body:**
```json
{
  "refresh_token": "<refresh_token saved from Step 4>"
}
```

**Verify:**
- Status: `200 OK`
- Returns a new `access_token`

---

### Step 6: Doctor Login

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `http://localhost:8001/api/v1/auth/doctor/login` |
| Auth | None |
| Body type | `x-www-form-urlencoded` |

**Body fields:**
```
username = drpriya@mityahar.com
password = Doctor@1234
```

**Verify:**
- Status: `200 OK`
- Response contains `access_token`

**Save:** Copy `access_token` → **`doctor_token`**

---

### Step 7: Google Verify *(Optional — only if testing Google Sign-In)*

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `http://localhost:8001/api/v1/auth/google/verify` |
| Auth | None |
| Body type | JSON |

**Body:**
```json
{
  "id_token": "<id_token from React Native GoogleSignin.getTokens()>"
}
```

**Verify:**
- Status: `200 OK`
- Returns `access_token`, `refresh_token`, `is_new_user` (boolean)
- If `is_new_user: true`, patient has no profile yet → navigate to onboarding

---

### Step 8: Get My Profile

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/users/me` |
| Auth | Bearer `patient_token` |

**Verify:**
- Status: `200 OK`
- Returns full patient profile; confirm `id` matches **`patient_id`**

---

### Step 9: Update My Profile

| Field | Value |
|---|---|
| Method | `PUT` |
| URL | `http://localhost:8001/api/v1/users/me` |
| Auth | Bearer `patient_token` |
| Body type | JSON |

**Body:**
```json
{
  "weight": 71,
  "activity_level": "VA",
  "region": "South"
}
```

**Verify:**
- Status: `200 OK`
- Response reflects updated `weight`, `activity_level`, `region`

---

### Step 10: Get BMI (via users route)

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/users/bmi` |
| Auth | Bearer `patient_token` |

**Verify:**
- Status: `200 OK`
- Returns `bmi` value calculated from current height and weight

---

### Step 11: Patient Onboarding

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `http://localhost:8001/api/v1/patients/onboarding` |
| Auth | Bearer `patient_token` |
| Body type | JSON |

**Body:**
```json
{
  "date_of_birth": "1997-06-15",
  "health_goals": ["weight_loss", "improve_energy"],
  "medical_conditions": ["None"],
  "food_allergies": ["None"],
  "target_weight_kg": 68.0,
  "meals_per_day": 5,
  "sleep_hours": 7.0,
  "water_glasses": 8,
  "occupation": "Software Engineer",
  "nonveg_meals_per_week": 0,
  "dietary_preferences": ["low_sugar"],
  "fasting_days": [],
  "smoking": false,
  "alcohol": false,
  "pace_preference": "moderate",
  "eating_habits": ["irregular_meals"]
}
```

**Verify:**
- Status: `200 OK`
- Response contains computed `bmi`, `bmr`, `tdee` (all non-null, non-zero)
- Auto-generated diet plan is created in the background (confirm via Step 20 below)

---

### Step 12: Accept Disclaimer

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `http://localhost:8001/api/v1/patients/disclaimer` |
| Auth | Bearer `patient_token` |

**Body:** *(none)*

**Verify:**
- Status: `200 OK`
- Response confirms `disclaimer_accepted_at` timestamp is now set

---

## Phase 3 — Subscription Activation

> **Goal:** Admin generates codes, doctor generates codes, patient activates a code to gain subscription access.

---

### Step 13: Generate Subscription Codes (Admin)

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `http://localhost:8001/api/v1/admin/codes/generate` |
| Auth | Bearer `admin_token` |
| Body type | JSON |

**Body:** *(use `doctor_id` saved from Step 2)*
```json
{
  "doctor_id": <doctor_id>,
  "count": 3,
  "expires_in_days": 30
}
```

**Verify:**
- Status: `201 Created`
- Returns array of 3 code strings, each 12-char alphanumeric
- No duplicates in the list

**Save:** Copy one code string → **`code`**

---

### Step 14: List All Codes (Admin)

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/admin/codes?doctor_id=<doctor_id>&is_used=false` |
| Auth | Bearer `admin_token` |

**Verify:**
- Status: `200 OK`
- Shows all unused codes for `doctor_id`; `is_used: false` for all

---

### Step 15: Generate Subscription Codes (Doctor)

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `http://localhost:8001/api/v1/doctor/subscription-codes` |
| Auth | Bearer `doctor_token` |
| Body type | JSON |

**Body:**
```json
{
  "count": 2,
  "expires_in_days": 30
}
```

**Verify:**
- Status: `201 Created`
- Returns 2 collision-safe 12-char codes owned by this doctor

---

### Step 16: List Doctor's Own Codes

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/doctor/subscription-codes` |
| Auth | Bearer `doctor_token` |

**Verify:**
- Status: `200 OK`
- Each entry shows `is_used`, `used_by_patient_id`, `used_at`
- Only codes belonging to this doctor appear

---

### Step 17: Activate Subscription (Patient)

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `http://localhost:8001/api/v1/patients/activate` |
| Auth | Bearer `patient_token` |
| Body type | JSON |

**Body:** *(use `code` saved from Step 13)*
```json
{
  "code": "<code>"
}
```

**Verify:**
- Status: `200 OK`
- `subscription_status` becomes `"active"`
- `doctor_id` is set to `doctor_id` saved from Step 2

---

### Step 18: Request Doctor Connection

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `http://localhost:8001/api/v1/patients/request-doctor` |
| Auth | Bearer `patient_token` |
| Body type | JSON |

**Body:**
```json
{
  "doctor_id": <doctor_id>
}
```

**Verify:**
- Status: `201 Created`
- Returns `request_id`
- Calling again with the same `doctor_id` returns `409 Conflict`

**Save:** Copy `id` from response → **`request_id`**

---

### Step 19: Check Request Status

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/patients/request-status` |
| Auth | Bearer `patient_token` |

**Verify:**
- Status: `200 OK`
- `status` field is one of: `pending`, `accepted`, `rejected`

---

## Phase 4 — Doctor Dashboard

> **Goal:** Doctor views their patient list, accepts requests, views plans and logs.

---

### Step 20: Doctor Dashboard

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/doctor/dashboard` |
| Auth | Bearer `doctor_token` |

**Verify:**
- Status: `200 OK`
- Response contains `total_patients`, `active_patients`, `pending_requests`, `plans_generated_this_week`, `inactive_patients` list, `expiring_soon` list

---

### Step 21: List My Patients (Doctor)

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/doctor/patients?page=1&page_size=20` |
| Auth | Bearer `doctor_token` |

**Verify:**
- Status: `200 OK`
- All returned patients have `doctor_id` matching this doctor
- No patients from other doctors appear

---

### Step 22: Get Single Patient (Doctor)

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/doctor/patients/<patient_id>` |
| Auth | Bearer `doctor_token` |

**Verify:**
- Status: `200 OK`
- Returns full patient profile
- If `patient_id` belongs to a different doctor → `404 Not Found`

---

### Step 23: List Pending Requests (Doctor)

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/doctor/requests` |
| Auth | Bearer `doctor_token` |

**Verify:**
- Status: `200 OK`
- Shows patients who called `POST /patients/request-doctor` for this doctor
- `request_id` from Step 18 should appear here

---

### Step 24: Accept a Patient Request

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `http://localhost:8001/api/v1/doctor/requests/<request_id>/accept` |
| Auth | Bearer `doctor_token` |

**Body:** *(none)*

**Verify:**
- Status: `200 OK`
- Patient's `doctor_id` is set, `subscription_status` = `"active"`

---

### Step 25: Reject a Patient Request *(use a separate test request)*

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `http://localhost:8001/api/v1/doctor/requests/<request_id>/reject` |
| Auth | Bearer `doctor_token` |
| Body type | JSON |

**Body:**
```json
{
  "rejection_note": "Not accepting new patients this month"
}
```

**Verify:**
- Status: `200 OK`
- Request `status` becomes `"rejected"`, `rejection_note` stored

---

### Step 26: Get Patient's Active Plan (Doctor)

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/doctor/patients/<patient_id>/plan` |
| Auth | Bearer `doctor_token` |

**Verify:**
- Status: `200 OK`
- Returns the patient's active plan (generated during onboarding)

---

### Step 27: View Patient Meal Logs (Doctor)

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/doctor/patients/<patient_id>/logs?days=7` |
| Auth | Bearer `doctor_token` |

**Verify:**
- Status: `200 OK`
- Returns last 7 days of meal logs for this patient

---

### Step 28: View Patient Progress (Doctor)

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/doctor/patients/<patient_id>/progress?days=30` |
| Auth | Bearer `doctor_token` |

**Verify:**
- Status: `200 OK`
- Returns weight/water/steps history for the last 30 days

---

### Step 29: Add Clinical Note

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `http://localhost:8001/api/v1/doctor/patients/<patient_id>/notes` |
| Auth | Bearer `doctor_token` |
| Body type | JSON |

**Body:**
```json
{
  "content": "Patient shows signs of irregular eating. Recommend 5-meal plan.",
  "note_type": "dietary",
  "is_private": true
}
```
`note_type` options: `general` | `dietary` | `medical` | `progress`

**Verify:**
- Status: `201 Created`
- Note stored with `doctor_id` of this doctor

---

### Step 30: Get Clinical Notes (Doctor)

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/doctor/patients/<patient_id>/notes` |
| Auth | Bearer `doctor_token` |

**Verify:**
- Status: `200 OK`
- Only notes written by this doctor for this patient appear

---

## Phase 5 — Meal Plan (Patient Perspective)

> **Goal:** Patient views their auto-generated diet plan, adjusts it, checks the weekly view and shopping list. Subscription must be active.

---

### Step 31: Calculate BMR

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/calculations/bmr` |
| Auth | Bearer `patient_token` |

**Verify:**
- Status: `200 OK`
- Returns `bmr` value (kcal/day) derived from patient's stored data

---

### Step 32: Calculate TDEE

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/calculations/tdee` |
| Auth | Bearer `patient_token` |

**Verify:**
- Status: `200 OK`
- Returns `tdee` value adjusted for activity level

---

### Step 33: Calculate BMI (via calculations route)

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/calculations/bmi` |
| Auth | Bearer `patient_token` |

**Verify:**
- Status: `200 OK`
- Returns `bmi` and classification (Underweight / Normal / Overweight / Obese)

---

### Step 34: Generate Diet Plan

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `http://localhost:8001/api/v1/diet-plans/generate` |
| Auth | Bearer `patient_token` |

**Body:** *(none — uses stored patient profile)*

**Verify:**
- Status: `200 OK` (or `503 Service Unavailable` only if all 3 internal retries fail)
- Returns 7-day plan with `meals` array populated for each day
- `ingredient_checklist` is present and non-empty
- Pantry staples are excluded from checklist

---

### Step 35: Get My Active Plan

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/diet-plans/my-plan` |
| Auth | Bearer `patient_token` |

**Verify:**
- Status: `200 OK`
- `is_active: true`
- `version` is a positive integer (≥1)

**Save:** Copy `id` from response → **`recommendation_id`**

---

### Step 36: Get Today's Meals

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/diet-plans/today` |
| Auth | Bearer `patient_token` |

**Verify:**
- Status: `200 OK`
- Returns only today's meals from the active plan (not all 7 days)

---

### Step 37: Update Plan (Patient Notes)

| Field | Value |
|---|---|
| Method | `PUT` |
| URL | `http://localhost:8001/api/v1/diet-plans/update` |
| Auth | Bearer `patient_token` |
| Body type | JSON |

**Body:**
```json
{
  "doctor_notes": "I prefer lighter breakfasts"
}
```

**Verify:**
- Status: `200 OK`
- `doctor_notes` field is updated in the plan
- `version` does NOT increment (in-place update, not a new version)

---

### Step 38: Get Ingredient Checklist

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/diet-plans/ingredient-checklist` |
| Auth | Bearer `patient_token` |

**Verify:**
- Status: `200 OK`
- Returns ingredients grouped by category
- Items with `is_pantry_staple=true` are excluded (salt, oil, spices, etc.)

---

### Step 39: Get Weekly Ingredients

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/diet-plans/weekly-ingredients` |
| Auth | Bearer `patient_token` |

**Verify:**
- Status: `200 OK`
- Full ingredient list for all 7 days (no pantry filtering)

---

### Step 40: Get Week View

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/meal-plan/week` |
| Auth | Bearer `patient_token` |

**Verify:**
- Status: `200 OK`
- Response is a dict with exactly 7 date-string keys (e.g. `"2026-03-07"`)
- Each key maps to that day's meals

---

### Step 41: Get Plan History

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/meal-plan/history` |
| Auth | Bearer `patient_token` |

**Verify:**
- Status: `200 OK`
- List of plan metadata (newest first): `version`, `created_at`, `is_active`
- Only one plan has `is_active: true`; rest are `false`

---

### Step 42: Get Shopping List

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/meal-plan/shopping-list` |
| Auth | Bearer `patient_token` |

**Verify:**
- Status: `200 OK`
- Items grouped by category
- Each item has `at_home` flag (boolean)
- Pantry staples excluded

---

### Step 43: Toggle Shopping Item

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `http://localhost:8001/api/v1/meal-plan/shopping-list/toggle` |
| Auth | Bearer `patient_token` |
| Body type | JSON |

**Body:**
```json
{
  "ingredient_name": "Basmati Rice",
  "at_home": true
}
```

**Verify:**
- Status: `200 OK`
- `at_home` is now `true` for "Basmati Rice" in the checklist

---

### Step 44: Adjust Meal Plan

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `http://localhost:8001/api/v1/meal-plan/adjust` |
| Auth | Bearer `patient_token` |
| Body type | JSON |

**Body:**
```json
{
  "adjustment_reason": "Too many calories"
}
```

**Verify:**
- Status: `200 OK`
- New plan `version` = previous version + 1 (verify via Step 35 after this)
- Yesterday's `calorie_adjustment` (if stored) is applied to `target_calories`

---

### Step 45: Delete Active Plan

| Field | Value |
|---|---|
| Method | `DELETE` |
| URL | `http://localhost:8001/api/v1/diet-plans/delete` |
| Auth | Bearer `patient_token` |

**Body:** *(none)*

**Verify:**
- Status: `200 OK`
- `is_active` becomes `false` for the current plan
- Re-run Step 35 → should return `404` or empty until a new plan is generated

---

## Phase 6 — Doctor Recipe & Plan Override

> **Goal:** Doctor adds a custom recipe (pending admin approval), assigns it to a patient, and overrides the patient's plan with notes.

---

### Step 46: Browse Recipes (Doctor)

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/doctor/recipes?diet_type=Vegetarian&meal_time=Breakfast&page=1&page_size=20` |
| Auth | Bearer `doctor_token` |

**Verify:**
- Status: `200 OK`
- Returns food items filtered by `diet_type` and `meal_time`

---

### Step 47: Add a Custom Recipe (Doctor)

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `http://localhost:8001/api/v1/doctor/recipes` |
| Auth | Bearer `doctor_token` |
| Body type | JSON |

**Body:**
```json
{
  "recipe_name": "Moong Dal Chilla",
  "slot_type": "main_dish",
  "cal_per_serving": 280,
  "protein_per_serving": 14,
  "carbs_per_serving": 38,
  "fat_per_serving": 6,
  "fiber_per_serving": 5,
  "diet_type": "Vegetarian",
  "meal_time_tags": ["Breakfast", "MorningSnacks"],
  "plan_type_tags": ["Healthy", "Diabetic-Friendly"],
  "ingredients": [
    {"name": "Moong Dal", "amount_g": 80},
    {"name": "Onion", "amount_g": 30},
    {"name": "Green Chilli", "amount_g": 5}
  ],
  "region_tags": ["North", "West"]
}
```

**Verify:**
- Status: `201 Created`
- `is_verified: false`, `source: "doctor"`
- This recipe will NOT appear in meal generation until admin approves it

**Save:** Copy `id` from response → **`recipe_id`**

---

### Step 48: Assign Recipe to Patient

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `http://localhost:8001/api/v1/doctor/recipes/<recipe_id>/assign` |
| Auth | Bearer `doctor_token` |
| Body type | JSON |

**Body:** *(use `patient_id` from Step 3 and `recipe_id` from Step 47)*
```json
{
  "patient_ids": [<patient_id>],
  "meal_type": "Breakfast",
  "meal_date": "2026-03-15",
  "note": "Try this instead of your usual breakfast tomorrow"
}
```

**Verify:**
- Status: `200 OK`
- `updated_count` = number of patients modified (should be 1)
- `failed_patient_ids` = empty list (would be non-empty if a patient_id belongs to a different doctor)

---

### Step 49: Override Patient's Plan (Doctor)

| Field | Value |
|---|---|
| Method | `PUT` |
| URL | `http://localhost:8001/api/v1/doctor/patients/<patient_id>/plan` |
| Auth | Bearer `doctor_token` |
| Body type | JSON |

**Body:** *(pass `meals: null` to keep existing meals and only update notes)*
```json
{
  "doctor_notes": "Reduce dinner carbs. Add protein at lunch.",
  "meals": null
}
```

**Verify:**
- Status: `200 OK`
- `doctor_notes` updated, `generated_by` = `"doctor"`
- Meals content unchanged (since `meals: null`)

---

### Step 50: Add Note to Specific Meal Slot

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `http://localhost:8001/api/v1/doctor/patients/<patient_id>/plan/notes` |
| Auth | Bearer `doctor_token` |
| Body type | JSON |

**Body:**
```json
{
  "meal_date": "2026-03-10",
  "meal_type": "Lunch",
  "note": "Avoid dal today, have paneer instead"
}
```

**Verify:**
- Status: `200 OK`
- Note injected into the specified meal slot
- If date+meal_type does not exist in the plan → `404 Not Found`

---

### Step 51: Remove Patient (Doctor)

| Field | Value |
|---|---|
| Method | `DELETE` |
| URL | `http://localhost:8001/api/v1/doctor/patients/<patient_id>` |
| Auth | Bearer `doctor_token` |

**Body:** *(none)*

**Verify:**
- Status: `200 OK`
- Patient `doctor_id` becomes `null`, `subscription_status` = `"inactive"`
- Patient account still exists (not deleted)

---

## Phase 7 — Progress & Streaks

> **Goal:** Patient logs meals (triggering calorie adjustment), logs water/steps/weight, checks adherence and streak. Subscription must be active.

---

### Step 52: Log a Meal

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `http://localhost:8001/api/v1/progress/log/meal` |
| Auth | Bearer `patient_token` |
| Body type | JSON |

**Body:**
```json
{
  "meal_type": "Breakfast",
  "calories": 420,
  "protein": 18,
  "carbs": 65,
  "fat": 8,
  "fiber": 4
}
```

**Verify:**
- Status: `201 Created`
- If `calories_consumed_today ≥ 80% of TDEE`, check that `calorie_adjustment` is written to `ProgressLog`

**Save:** Copy `id` from response → **`log_id`**

---

### Step 53: Log a Meal (with recommendation_id for adherence)

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `http://localhost:8001/api/v1/progress/log/meal` |
| Auth | Bearer `patient_token` |
| Body type | JSON |

**Body:** *(use `recommendation_id` saved from Step 35)*
```json
{
  "meal_type": "Lunch",
  "calories": 550,
  "protein": 22,
  "carbs": 80,
  "fat": 10,
  "fiber": 6,
  "recommendation_id": <recommendation_id>
}
```

**Verify:**
- Status: `201 Created`
- This meal will count toward adherence percentage (Step 67)

---

### Step 54: Edit Meal Log (within 24 hours)

| Field | Value |
|---|---|
| Method | `PUT` |
| URL | `http://localhost:8001/api/v1/progress/log/meal/<log_id>` |
| Auth | Bearer `patient_token` |
| Body type | JSON |

**Body:** *(use `log_id` from Step 52)*
```json
{
  "calories": 380,
  "protein": 15
}
```

**Verify:**
- Status: `200 OK`
- `calories` updated to `380`, `protein` to `15`

---

### Step 55: Delete Meal Log (within 24 hours)

| Field | Value |
|---|---|
| Method | `DELETE` |
| URL | `http://localhost:8001/api/v1/progress/log/meal/<log_id>` |
| Auth | Bearer `patient_token` |

**Body:** *(none)*

**Verify:**
- Status: `200 OK`
- Log is removed; `GET /progress/today` calories decrease accordingly

---

### Step 56: Log Water (cumulative add)

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `http://localhost:8001/api/v1/progress/log/water` |
| Auth | Bearer `patient_token` |
| Body type | JSON |

**Body:**
```json
{
  "glasses": 3
}
```

**Verify:**
- Status: `200 OK`
- Today's `water_glasses` increases by 3 (cumulative, not overwrite)

---

### Step 57: Update Water (overwrite)

| Field | Value |
|---|---|
| Method | `PUT` |
| URL | `http://localhost:8001/api/v1/progress/log/water` |
| Auth | Bearer `patient_token` |
| Body type | JSON |

**Body:**
```json
{
  "glasses": 6
}
```

**Verify:**
- Status: `200 OK`
- `water_glasses` is now exactly `6` (overwrites previous value)

---

### Step 58: Delete Water Log

| Field | Value |
|---|---|
| Method | `DELETE` |
| URL | `http://localhost:8001/api/v1/progress/log/water` |
| Auth | Bearer `patient_token` |

**Body:** *(none)*

**Verify:**
- Status: `200 OK`
- `water_glasses` resets to `0`

---

### Step 59: Log Steps (cumulative add)

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `http://localhost:8001/api/v1/progress/log/steps` |
| Auth | Bearer `patient_token` |
| Body type | JSON |

**Body:**
```json
{
  "steps": 4000
}
```

**Verify:**
- Status: `200 OK`
- Today's `steps` increases by 4000

---

### Step 60: Update Steps (overwrite)

| Field | Value |
|---|---|
| Method | `PUT` |
| URL | `http://localhost:8001/api/v1/progress/log/steps` |
| Auth | Bearer `patient_token` |
| Body type | JSON |

**Body:**
```json
{
  "steps": 8500
}
```

**Verify:**
- Status: `200 OK`
- `steps` is now exactly `8500`

---

### Step 61: Delete Steps Log

| Field | Value |
|---|---|
| Method | `DELETE` |
| URL | `http://localhost:8001/api/v1/progress/log/steps` |
| Auth | Bearer `patient_token` |

**Body:** *(none)*

**Verify:**
- Status: `200 OK`
- `steps` resets to `0`

---

### Step 62: Log Weight

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `http://localhost:8001/api/v1/progress/log/weight` |
| Auth | Bearer `patient_token` |
| Body type | JSON |

**Body:**
```json
{
  "weight": 71.5
}
```

**Verify:**
- Status: `200 OK`
- Today's weight entry is created at `71.5 kg`

---

### Step 63: Update Weight

| Field | Value |
|---|---|
| Method | `PUT` |
| URL | `http://localhost:8001/api/v1/progress/log/weight` |
| Auth | Bearer `patient_token` |
| Body type | JSON |

**Body:**
```json
{
  "weight": 71.2
}
```

**Verify:**
- Status: `200 OK`
- Today's weight entry is now `71.2 kg`

---

### Step 64: Log Activity

| Field | Value |
|---|---|
| Method | `POST` |
| URL | `http://localhost:8001/api/v1/progress/log/activity` |
| Auth | Bearer `patient_token` |
| Body type | JSON |

**Body:**
```json
{
  "steps": 6000,
  "calories_burned": 280,
  "activity_type": "Cycling"
}
```

**Verify:**
- Status: `200 OK`
- `steps` and `calories_burned` recorded for today

---

### Step 65: Today's Summary

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/progress/today` |
| Auth | Bearer `patient_token` |

**Verify:**
- Status: `200 OK`
- `calories_consumed` vs `target` (must use patient's real TDEE, not hardcoded 2000 — verify if TDEE is set)
- `water_glasses`, `steps` vs targets shown

---

### Step 66: Weekly Summary

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/progress/weekly` |
| Auth | Bearer `patient_token` |

**Verify:**
- Status: `200 OK`
- Returns daily calorie totals for the last 7 days

---

### Step 67: Weekly Report (Detailed)

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/progress/weekly-report` |
| Auth | Bearer `patient_token` |

**Verify:**
- Status: `200 OK`
- Returns per-day breakdown: macros + water + steps vs TDEE targets
- Includes averages for the 7-day window

---

### Step 68: Weight History

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/progress/weight-history?days=30` |
| Auth | Bearer `patient_token` |

**Verify:**
- Status: `200 OK`
- Returns up to 30 entries with `log_date` and `weight_kg`

---

### Step 69: Get Current Weight

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/progress/weight` |
| Auth | Bearer `patient_token` |

**Verify:**
- Status: `200 OK`
- Returns current `weight_kg` from patient profile

---

### Step 70: Streak

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/progress/streak` |
| Auth | Bearer `patient_token` |

**Verify:**
- Status: `200 OK`
- `streak_days` = consecutive days with at least one meal logged
- Value is stored on `ProgressLog` for today

---

### Step 71: Weekly Adherence

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/progress/adherence/weekly?days=7` |
| Auth | Bearer `patient_token` |

**Verify:**
- Status: `200 OK`
- `overall_adherence_pct` and per-day breakdown returned
- Only meals logged with a valid `recommendation_id` count toward adherence (Step 53 should contribute; Step 52 should not)

---

## Phase 8 — Admin Oversight

> **Goal:** Admin reviews the platform state, manages food items, checks audit logs and billing.

---

### Step 72: Platform Stats

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/admin/stats` |
| Auth | Bearer `admin_token` |

**Verify:**
- Status: `200 OK`
- Returns `total_patients`, `active_subscriptions`, `total_doctors`, `total_plans_generated`

---

### Step 73: List All Doctors (Admin)

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/admin/doctors` |
| Auth | Bearer `admin_token` |

**Verify:**
- Status: `200 OK`
- Dr. Priya Mehta (`doctor_id` from Step 2) appears in the list

---

### Step 74: Get Doctor Detail (Admin)

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/admin/doctors/<doctor_id>` |
| Auth | Bearer `admin_token` |

**Verify:**
- Status: `200 OK`
- Returns doctor profile + patient count

---

### Step 75: Deactivate Doctor (Admin)

| Field | Value |
|---|---|
| Method | `PATCH` |
| URL | `http://localhost:8001/api/v1/admin/doctors/<doctor_id>/deactivate` |
| Auth | Bearer `admin_token` |

**Body:** *(none)*

**Verify:**
- Status: `200 OK`
- Doctor `is_active` becomes `false`

---

### Step 76: Delete Doctor (Admin)

| Field | Value |
|---|---|
| Method | `DELETE` |
| URL | `http://localhost:8001/api/v1/admin/doctors/<doctor_id>` |
| Auth | Bearer `admin_token` |

**Body:** *(none)*

**Verify:**
- Status: `200 OK`
- Doctor soft-deleted; all connected patients set to `standalone` + `inactive`

> ⚠️ **Warning:** Use a throwaway doctor for this test, not the one used in earlier steps if you still need it.

---

### Step 77: Override Patient Subscription (Admin)

| Field | Value |
|---|---|
| Method | `PATCH` |
| URL | `http://localhost:8001/api/v1/admin/patients/<patient_id>/subscription/override?status=active&days=30` |
| Auth | Bearer `admin_token` |

**Body:** *(none)*

**Verify:**
- Status: `200 OK`
- Patient `subscription_status` = `"active"`, `subscription_end_date` set 30 days out

---

### Step 78: List Food Items (Admin)

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/admin/food?source=doctor&is_verified=false` |
| Auth | Bearer `admin_token` |

**Verify:**
- Status: `200 OK`
- "Moong Dal Chilla" (added in Step 47) appears here with `is_verified: false`

**Save:** Copy `id` of "Moong Dal Chilla" → **`food_id`**

---

### Step 79: Approve Food Item (Admin)

| Field | Value |
|---|---|
| Method | `PATCH` |
| URL | `http://localhost:8001/api/v1/admin/food/<food_id>/approve` |
| Auth | Bearer `admin_token` |

**Body:** *(none)*

**Verify:**
- Status: `200 OK`
- `is_verified` becomes `true`; item now eligible for meal generation

---

### Step 80: Reject Food Item (Admin)

| Field | Value |
|---|---|
| Method | `PATCH` |
| URL | `http://localhost:8001/api/v1/admin/food/<food_id>/reject?reason=Incorrect+nutrition+data` |
| Auth | Bearer `admin_token` |

**Verify:**
- Status: `200 OK`
- `source` becomes `"rejected"`; item excluded from all generation

---

### Step 81: Delete Food Item (Admin)

| Field | Value |
|---|---|
| Method | `DELETE` |
| URL | `http://localhost:8001/api/v1/admin/food/<food_id>` |
| Auth | Bearer `admin_token` |

**Body:** *(none)*

**Verify:**
- Status: `200 OK`
- Hard-delete confirmed; item no longer appears in `/admin/food`

---

### Step 82: Audit Logs

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/admin/audit-logs?actor_role=admin&action=delete&page=1&page_size=20` |
| Auth | Bearer `admin_token` |

**Verify:**
- Status: `200 OK`
- Delete actions from Steps 76 and 81 appear here
- Each entry has `actor_id`, `actor_role`, `action`, `entity_type`, `entity_id`, `ip_address`

---

### Step 83: Billing Overview

| Field | Value |
|---|---|
| Method | `GET` |
| URL | `http://localhost:8001/api/v1/admin/billing` |
| Auth | Bearer `admin_token` |

**Verify:**
- Status: `200 OK`
- Returns `total_codes_issued`, `total_codes_used`, and a per-doctor breakdown

---

### Step 84: Erase Patient Data — DPDP *(Use a throwaway patient only)*

| Field | Value |
|---|---|
| Method | `DELETE` |
| URL | `http://localhost:8001/api/v1/admin/patients/<patient_id>` |
| Auth | Bearer `admin_token` |

**Body:** *(none)*

**Verify:**
- Status: `200 OK`
- PII fields are anonymised (name, email replaced with placeholders)
- All meal logs and progress logs are hard-deleted

> ⚠️ **Warning:** This is irreversible. Do NOT run on the main test patient unless you want to rebuild from Step 3.

---

## Error Cases to Test

These should each return a `4xx` error. Test them deliberately to confirm auth and isolation are enforced.

---

### EC-1: Patient token on a Doctor-only endpoint

| | |
|---|---|
| Request | `GET http://localhost:8001/api/v1/doctor/dashboard` with Bearer `patient_token` |
| Expected | `403 Forbidden` or `401 Unauthorized` |
| Why | `doctor_token` required; patient JWT has `role: "patient"`, not `"doctor"` |

---

### EC-2: Doctor token on an Admin-only endpoint

| | |
|---|---|
| Request | `GET http://localhost:8001/api/v1/admin/stats` with Bearer `doctor_token` |
| Expected | `403 Forbidden` or `401 Unauthorized` |
| Why | `admin_token` required; doctor JWT role does not satisfy admin guard |

---

### EC-3: Doctor accessing another doctor's patient

| | |
|---|---|
| Setup | Create a second doctor (Step 2 with a different email). Log in as that doctor. Use their token. |
| Request | `GET http://localhost:8001/api/v1/doctor/patients/<patient_id>` with the second doctor's token (patient belongs to first doctor) |
| Expected | `404 Not Found` |
| Why | `DoctorIsolationMiddleware` injects `request.state.doctor_id`; query filters by it — different doctor sees nothing |

---

### EC-4: Using an already-used subscription code

| | |
|---|---|
| Setup | Use a code that was already consumed in Step 17 |
| Request | `POST /patients/activate` with Bearer `patient_token`, body `{ "code": "<already used code>" }` |
| Expected | `400 Bad Request` or `409 Conflict` |
| Why | `is_used: true` on the code; activation rejects reuse |

---

### EC-5: Using an expired subscription code

| | |
|---|---|
| Setup | Generate a code with `expires_in_days: 0` or manipulate `expires_at` in DB to a past date |
| Request | `POST /patients/activate` with that code |
| Expected | `400 Bad Request` — "Code expired" |
| Why | Server checks `expires_at < now()` before activating |

---

### EC-6: Editing a meal log older than 24 hours

| | |
|---|---|
| Setup | Use a `log_id` from a meal logged yesterday or earlier |
| Request | `PUT /progress/log/meal/<old_log_id>` with Bearer `patient_token`, body `{ "calories": 200 }` |
| Expected | `403 Forbidden` or `400 Bad Request` — "Edit window expired" |
| Why | 24-hour edit window enforced in `progress_service.update_meal_log()` |

---

### EC-7: Patient accessing subscription-gated endpoint without active subscription

| | |
|---|---|
| Setup | Ensure patient `subscription_status = "inactive"` (new patient before activation, or after Step 84) |
| Request | `POST /diet-plans/generate` with Bearer `patient_token` |
| Expected | `402 Payment Required` |
| Why | `SubscriptionCheckMiddleware` reads `sub_status` from JWT; blocks inactive patients on gated routes |

---

### EC-8: Duplicate doctor request

| | |
|---|---|
| Request | Call `POST /patients/request-doctor` a second time with the same `doctor_id` |
| Expected | `409 Conflict` |
| Why | Duplicate pending request detection enforced in the endpoint |

---

### EC-9: No auth header on a protected endpoint

| | |
|---|---|
| Request | `GET /users/me` with no Authorization header |
| Expected | `401 Unauthorized` |
| Why | JWT dependency guard requires a valid Bearer token |

---

### EC-10: Diet plan endpoints with no active plan

| | |
|---|---|
| Setup | Run Step 45 (delete active plan), then immediately call Step 36 |
| Request | `GET /diet-plans/today` with Bearer `patient_token` |
| Expected | `404 Not Found` |
| Why | No active plan exists; service returns 404 |

---

*End of Mityahar API Manual Testing Guide — 84 endpoints covered across 8 phases.*
