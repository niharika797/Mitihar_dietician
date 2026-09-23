
# MITYAHAR API — COMPLETE TESTING GUIDE

## YOUR TASK
Read this document fully. Then produce a single, well-structured Markdown testing guide
that I can follow step-by-step in Postman or Insomnia to test every endpoint in the
Mityahar API. Do not write any code. Do not modify any files.

---

## CONTEXT
- Base URL: http://localhost:8001/api/v1
- Auth: Bearer token (JWT). Get it from login endpoints, paste into Authorization header.
- Content-Type: application/json for all JSON bodies.
- Form-encoded: login endpoints use x-www-form-urlencoded (username + password fields).
- The server runs with: venv\Scripts\uvicorn app.main:app --reload --port 8001

---

## TESTING FLOW (must follow this order — later steps depend on earlier ones)

### PHASE 1 — ADMIN SETUP
Admin creates a doctor account. This is always the first step.

### PHASE 2 — PATIENT REGISTRATION & ONBOARDING
Patient registers, then completes onboarding (which also auto-generates their first diet plan).

### PHASE 3 — SUBSCRIPTION ACTIVATION
Admin generates codes for the doctor. Doctor generates codes. Patient activates.

### PHASE 4 — DOCTOR DASHBOARD
Doctor views patients, plans, logs, clinical notes.

### PHASE 5 — MEAL PLAN (PATIENT PERSPECTIVE)
Patient views plan, adjusts it, logs meals, tracks progress.

### PHASE 6 — DOCTOR RECIPE & PLAN OVERRIDE
Doctor adds a recipe, assigns it to patient, overrides plan with notes.

### PHASE 7 — PROGRESS & STREAKS
Patient logs water, steps, weight, checks adherence.

### PHASE 8 — ADMIN OVERSIGHT
Admin views audit logs, stats, billing, manages food items.

---

## ALL ENDPOINTS + EXACT INPUTS

Below is every endpoint grouped by role. For each one, produce:
- Method + full URL
- Auth required (none / patient token / doctor token / admin token)
- Exact request body or query params
- What to check in the response
- Any token or ID to save for later steps

---

### AUTH ENDPOINTS

**1. Admin Login**
POST /auth/admin/login
Auth: none
Body (form-urlencoded):
  username=admin@mityahar.com
  password=Admin@1234
Save: admin_token

**2. Patient Register**
POST /auth/register
Auth: none
Body (JSON):
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
Save: note the user_id from response

**3. Patient Login**
POST /auth/token
Auth: none
Body (form-urlencoded):
  username=testpatient@gmail.com
  password=Patient@123
Save: patient_token, refresh_token

**4. Refresh Token**
POST /auth/refresh
Auth: none
Body (JSON):
{ "refresh_token": "<refresh_token from step 3>" }

**5. Doctor Login**
POST /auth/doctor/login
Auth: none
Body (form-urlencoded):
  username=<doctor email created by admin in step below>
  password=Doctor@1234
Save: doctor_token

**6. Google Verify (optional — only if testing Google Sign-In)**
POST /auth/google/verify
Auth: none
Body (JSON):
{ "id_token": "<id_token from React Native GoogleSignin.getTokens()>" }
Check: returns access_token, refresh_token, is_new_user

---

### ADMIN ENDPOINTS (all require admin_token)

**7. Create Doctor**
POST /admin/doctors
Auth: admin_token
Body (JSON):
{
  "email": "drpriya@mityahar.com",
  "password": "Doctor@1234",
  "name": "Dr. Priya Mehta",
  "phone": "9876543210",
  "specialization": "Dietitian",
  "clinic_name": "Healthy Roots Clinic",
  "city": "Mumbai"
}
Save: doctor_id from response

**8. List All Doctors**
GET /admin/doctors
Auth: admin_token

**9. Get Doctor Detail**
GET /admin/doctors/{doctor_id}
Auth: admin_token

**10. Deactivate Doctor**
PATCH /admin/doctors/{doctor_id}/deactivate
Auth: admin_token
(no body)

**11. Delete Doctor**
DELETE /admin/doctors/{doctor_id}
Auth: admin_token
(no body — soft deletes, disconnects patients)

**12. Platform Stats**
GET /admin/stats
Auth: admin_token
Check: total_patients, active_subscriptions, total_doctors, total_plans_generated

**13. Generate Subscription Codes (admin)**
POST /admin/codes/generate
Auth: admin_token
Body (JSON):
{
  "doctor_id": <doctor_id from step 7>,
  "count": 3,
  "expires_in_days": 30
}
Save: one of the code strings

**14. List All Codes**
GET /admin/codes
Auth: admin_token
Optional query params: ?doctor_id=1&is_used=false

**15. Override Patient Subscription**
PATCH /admin/patients/{patient_id}/subscription/override?status=active&days=30
Auth: admin_token
(no body)

**16. List Food Items**
GET /admin/food
Auth: admin_token
Optional: ?source=doctor&is_verified=false

**17. Approve Food Item**
PATCH /admin/food/{food_id}/approve
Auth: admin_token

**18. Reject Food Item**
PATCH /admin/food/{food_id}/reject?reason=Incorrect+nutrition+data
Auth: admin_token

**19. Delete Food Item**
DELETE /admin/food/{food_id}
Auth: admin_token

**20. Audit Logs**
GET /admin/audit-logs
Auth: admin_token
Optional: ?actor_role=admin&action=delete&page=1&page_size=20

**21. Billing Overview**
GET /admin/billing
Auth: admin_token
Check: total_codes_issued, total_codes_used, per-doctor breakdown

**22. Erase Patient Data (DPDP)**
DELETE /admin/patients/{patient_id}
Auth: admin_token
WARNING: Anonymises PII and hard-deletes all logs. Use a test patient only.

---

### PATIENT ENDPOINTS (all require patient_token)

**23. Get My Profile**
GET /users/me
Auth: patient_token

**24. Update My Profile**
PUT /users/me
Auth: patient_token
Body (JSON):
{
  "weight": 71,
  "activity_level": "VA",
  "region": "South"
}

**25. Get BMI**
GET /users/bmi
Auth: patient_token

**26. Onboarding**
POST /patients/onboarding
Auth: patient_token
Body (JSON):
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
Check: bmi, bmr, tdee are populated in response
Check: auto-generated diet plan was created (verify via GET /diet-plans/my-plan next)

**27. Activate Subscription**
POST /patients/activate
Auth: patient_token
Body (JSON):
{ "code": "<code from step 13 or step 36>" }
Check: subscription_status becomes "active", doctor_id is set

**28. Request Doctor Connection**
POST /patients/request-doctor
Auth: patient_token
Body (JSON):
{ "doctor_id": <doctor_id> }
Check: 201, request_id returned
Check: 409 if called again with same doctor

**29. Check Request Status**
GET /patients/request-status
Auth: patient_token
Check: status field (pending / accepted / rejected)

**30. Accept Disclaimer**
POST /patients/disclaimer
Auth: patient_token
(no body)

---

### CALCULATIONS ENDPOINTS (require patient_token)

**31. Calculate BMR**
GET /calculations/bmr
Auth: patient_token

**32. Calculate TDEE**
GET /calculations/tdee
Auth: patient_token

**33. Calculate BMI**
GET /calculations/bmi
Auth: patient_token

---

### DIET PLAN ENDPOINTS (require patient_token, subscription must be active)

**34. Generate Diet Plan**
POST /diet-plans/generate
Auth: patient_token
(no body — uses patient profile data)
Check: 7-day plan returned, meals array populated, ingredient_checklist present
Note: retries up to 3 times internally, returns 503 if all fail

**35. Get My Active Plan**
GET /diet-plans/my-plan
Auth: patient_token
Check: is_active=true, version number

**36. Get Today's Meals**
GET /diet-plans/today
Auth: patient_token
Check: returns only today's meals from the active plan

**37. Update Plan (patient notes)**
PUT /diet-plans/update
Auth: patient_token
Body (JSON):
{ "doctor_notes": "I prefer lighter breakfasts" }

**38. Get Ingredient Checklist**
GET /diet-plans/ingredient-checklist
Auth: patient_token
Check: list of ingredients grouped by category, pantry staples excluded

**39. Get Weekly Ingredients**
GET /diet-plans/weekly-ingredients
Auth: patient_token

**40. Delete Active Plan**
DELETE /diet-plans/delete
Auth: patient_token

---

### MEAL PLAN ENDPOINTS (require patient_token, subscription must be active)

**41. Adjust Meal Plan**
POST /meal-plan/adjust
Auth: patient_token
Body (JSON):
{ "adjustment_reason": "Too many calories" }
Check: new plan version incremented (version+1)
Check: yesterday's calorie_adjustment applied if logged yesterday

**42. Get Week View**
GET /meal-plan/week
Auth: patient_token
Check: dict keyed by date strings, 7 days

**43. Get Plan History**
GET /meal-plan/history
Auth: patient_token
Check: list of past plans with version, created_at, is_active

**44. Get Shopping List**
GET /meal-plan/shopping-list
Auth: patient_token
Check: items grouped by category, at_home flag present

**45. Toggle Shopping Item**
POST /meal-plan/shopping-list/toggle
Auth: patient_token
Body (JSON):
{ "ingredient_name": "Basmati Rice", "at_home": true }

---

### PROGRESS ENDPOINTS (require patient_token, subscription must be active)

**46. Log a Meal**
POST /progress/log/meal
Auth: patient_token
Body (JSON):
{
  "meal_type": "Breakfast",
  "calories": 420,
  "protein": 18,
  "carbs": 65,
  "fat": 8,
  "fiber": 4
}
Check: if calories logged >= 80% of TDEE, calorie_adjustment is stored

**47. Log a Meal (with recommendation_id for adherence tracking)**
POST /progress/log/meal
Auth: patient_token
Body (JSON):
{
  "meal_type": "Lunch",
  "calories": 550,
  "protein": 22,
  "carbs": 80,
  "fat": 10,
  "fiber": 6,
  "recommendation_id": <id from GET /diet-plans/my-plan>
}

**48. Edit Meal Log (within 24 hours)**
PUT /progress/log/meal/{log_id}
Auth: patient_token
Body (JSON):
{ "calories": 380, "protein": 15 }

**49. Delete Meal Log (within 24 hours)**
DELETE /progress/log/meal/{log_id}
Auth: patient_token

**50. Log Water**
POST /progress/log/water
Auth: patient_token
Body (JSON): { "glasses": 3 }

**51. Update Water (overwrite)**
PUT /progress/log/water
Auth: patient_token
Body (JSON): { "glasses": 6 }

**52. Delete Water Log**
DELETE /progress/log/water
Auth: patient_token

**53. Log Steps**
POST /progress/log/steps
Auth: patient_token
Body (JSON): { "steps": 4000 }

**54. Update Steps (overwrite)**
PUT /progress/log/steps
Auth: patient_token
Body (JSON): { "steps": 8500 }

**55. Delete Steps Log**
DELETE /progress/log/steps
Auth: patient_token

**56. Log Weight**
POST /progress/log/weight
Auth: patient_token
Body (JSON): { "weight": 71.5 }

**57. Update Weight**
PUT /progress/log/weight
Auth: patient_token
Body (JSON): { "weight": 71.2 }

**58. Log Activity**
POST /progress/log/activity
Auth: patient_token
Body (JSON):
{
  "steps": 6000,
  "calories_burned": 280,
  "activity_type": "Cycling"
}

**59. Today's Summary**
GET /progress/today
Auth: patient_token
Check: calories consumed vs target (uses real TDEE), water glasses, steps

**60. Weekly Summary**
GET /progress/weekly
Auth: patient_token
Check: daily calorie breakdown for last 7 days

**61. Weekly Report (detailed)**
GET /progress/weekly-report
Auth: patient_token
Check: daily breakdown with macros + targets + averages

**62. Weight History**
GET /progress/weight-history?days=30
Auth: patient_token

**63. Get Current Weight**
GET /progress/weight
Auth: patient_token

**64. Streak**
GET /progress/streak
Auth: patient_token
Check: streak_days (consecutive days with at least one meal logged)

**65. Weekly Adherence**
GET /progress/adherence/weekly?days=7
Auth: patient_token
Check: overall_adherence_pct, daily breakdown
Note: only meals with recommendation_id count toward adherence

---

### DOCTOR ENDPOINTS (all require doctor_token)

**66. Doctor Dashboard**
GET /doctor/dashboard
Auth: doctor_token
Check: total_patients, active_patients, pending_requests, plans_generated_this_week,
       inactive_patients list, expiring_soon list

**67. List My Patients (paginated)**
GET /doctor/patients?page=1&page_size=20
Auth: doctor_token
Check: only patients whose doctor_id = this doctor

**68. Get Single Patient**
GET /doctor/patients/{patient_id}
Auth: doctor_token
Check: 404 if patient belongs to a different doctor

**69. Get Patient's Active Plan**
GET /doctor/patients/{patient_id}/plan
Auth: doctor_token

**70. Override Patient's Plan**
PUT /doctor/patients/{patient_id}/plan
Auth: doctor_token
Body (JSON):
{
  "doctor_notes": "Reduce dinner carbs. Add protein at lunch.",
  "meals": null
}
Note: meals=null keeps existing meals, only updates notes.
To replace meals: pass the full meals array.

**71. Add Note to Specific Meal Slot**
POST /doctor/patients/{patient_id}/plan/notes
Auth: doctor_token
Body (JSON):
{
  "meal_date": "2026-03-10",
  "meal_type": "Lunch",
  "note": "Avoid dal today, have paneer instead"
}
Check: 404 if date+meal_type not found in plan

**72. View Patient Meal Logs**
GET /doctor/patients/{patient_id}/logs?days=7
Auth: doctor_token
Check: only this doctor's patient's logs

**73. View Patient Progress**
GET /doctor/patients/{patient_id}/progress?days=30
Auth: doctor_token
Check: weight/water/steps history

**74. Add Clinical Note**
POST /doctor/patients/{patient_id}/notes
Auth: doctor_token
Body (JSON):
{
  "content": "Patient shows signs of irregular eating. Recommend 5-meal plan.",
  "note_type": "dietary",
  "is_private": true
}
note_type options: general | dietary | medical | progress

**75. Get Clinical Notes**
GET /doctor/patients/{patient_id}/notes
Auth: doctor_token
Check: only notes written by this doctor for this patient

**76. List Pending Requests**
GET /doctor/requests
Auth: doctor_token
Check: patients who requested this doctor via POST /patients/request-doctor

**77. Accept a Request**
POST /doctor/requests/{request_id}/accept
Auth: doctor_token
(no body)
Check: patient.doctor_id is now set, subscription_status="active"

**78. Reject a Request**
POST /doctor/requests/{request_id}/reject
Auth: doctor_token
Body (JSON):
{ "rejection_note": "Not accepting new patients this month" }

**79. Generate Subscription Codes**
POST /doctor/subscription-codes
Auth: doctor_token
Body (JSON):
{
  "count": 2,
  "expires_in_days": 30
}
Save: one code for patient activation test
Check: collision-safe 12-char alphanumeric codes

**80. List My Codes**
GET /doctor/subscription-codes
Auth: doctor_token
Check: shows is_used, used_by_patient_id, used_at

**81. Browse Recipes**
GET /doctor/recipes?diet_type=Vegetarian&meal_time=Breakfast&page=1&page_size=20
Auth: doctor_token
Optional: ?search=dal

**82. Add a Custom Recipe**
POST /doctor/recipes
Auth: doctor_token
Body (JSON):
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
Check: is_verified=false, source="doctor"
Save: recipe_id
Note: Admin must approve via PATCH /admin/food/{id}/approve before it enters meal generation

**83. Assign Recipe to Patients**
POST /doctor/recipes/{recipe_id}/assign
Auth: doctor_token
Body (JSON):
{
  "patient_ids": [<patient_id>],
  "meal_type": "Breakfast",
  "meal_date": "2026-03-15",
  "note": "Try this instead of your usual breakfast tomorrow"
}
Check: updated_count = number of patients whose plan was modified
Check: failed_patient_ids = patients not belonging to this doctor (isolation check)

**84. Remove Patient**
DELETE /doctor/patients/{patient_id}
Auth: doctor_token
(no body)
Check: patient.doctor_id becomes null, subscription_status="inactive"
Note: patient account is NOT deleted

---

## OUTPUT FORMAT REQUIRED

Produce the guide as a Markdown document structured exactly like this:

# Mityahar API — Manual Testing Guide

## Setup
[Postman/Insomnia setup instructions, base URL, how to set Bearer token]

## Variables to Track
[A table listing tokens and IDs to save across steps: admin_token, doctor_token, patient_token, doctor_id, patient_id, code, recommendation_id, log_id, recipe_id]

## Phase 1 — Admin Setup
### Step 1: Admin Login
[method, URL, body, expected response, what to save]

### Step 2: Create Doctor
...

[Continue for all 84 endpoints across all phases]

## Error Cases to Test
[For each major endpoint, list one "should fail" case: wrong token role, wrong doctor's patient, expired code, etc.]

---

## IMPORTANT RULES FOR THE OUTPUT
1. Every step must include the EXACT JSON body or form fields — no "fill in your value" placeholders except for tokens/IDs saved from previous steps.
2. Every step must say what auth token to use.
3. Every step must say what to verify in the response.
4. Steps that depend on a previous step's output (e.g. doctor_id) must say explicitly "use doctor_id saved from Step 7".
5. Do NOT abbreviate. Every single endpoint listed above must appear in the output.
6. The error cases section must include at minimum: trying a patient token on a doctor endpoint, trying a doctor token on another doctor's patient, using an expired/used subscription code, editing a meal log older than 24 hours.
