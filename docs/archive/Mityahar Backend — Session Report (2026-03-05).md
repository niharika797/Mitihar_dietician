# Mityahar Backend — Session Report (2026-03-05)

## Overview

This session delivered **two major changes** to the Mityahar FastAPI backend: adding calorie adjustment tracking to progress logs, and migrating the legacy [DietPlan](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/services/diet_plan_service.py#42-132) model to a proper Pydantic schema with several logic fixes.

---

## 1. Calorie Adjustment for Progress Logs

**Goal:** Automatically calculate and store how much a patient is over/under their TDEE each day.

### Changes Made

| Action | File | What Changed |
|--------|------|-------------|
| MODIFY | [db_models.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/models/db_models.py) | Added `calorie_adjustment = Column(Numeric, nullable=True)` to [ProgressLog](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/models/db_models.py#239-263) after `streak_days` |
| MODIFY | [progress_service.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/services/progress_service.py) | Added [calculate_and_store_calorie_adjustment()](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/services/progress_service.py#148-179) — sums today's calories, computes `tdee - today_calories`, stores on the [ProgressLog](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/models/db_models.py#239-263) row |
| MODIFY | [progress.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/routers/progress.py) | [post_log_meal](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/routers/progress.py#19-28) now checks if daily total ≥ 80% of TDEE and triggers the adjustment calculation |
| MIGRATE | [861b9d58abdf](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/alembic/versions/861b9d58abdf_add_calorie_adjustment_to_progress_logs.py) | Alembic migration — clean, no GIN index false positives, applied successfully |

### How It Works

```
Patient logs a meal → post_log_meal
  ↓
  log_meal() persists the meal
  ↓
  if patient.tdee exists:
    get today's total calories
    if total ≥ 80% of TDEE:
      adjustment = TDEE - total_calories
      store on ProgressLog.calorie_adjustment
```

> **Positive adjustment** = deficit (ate less than TDEE, eat more tomorrow)
> **Negative adjustment** = surplus (ate more than TDEE, eat less tomorrow)

---

## 2. Legacy DietPlan Migration & Logic Fixes

**Goal:** Replace [app/models/diet_plan.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/models/diet_plan.py) with a proper schema, enable plan regeneration, and use stored TDEE.

### Changes Made

| Action | File | What Changed |
|--------|------|-------------|
| CREATE | [diet_plan.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/schemas/diet_plan.py) | New [DietPlanResponse](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/schemas/diet_plan.py#5-16) Pydantic schema matching the old [DietPlan](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/services/diet_plan_service.py#42-132) fields exactly |
| MODIFY | [diet_plans.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/routers/diet_plans.py) | Import swapped; regeneration block now **deletes** the old plan instead of raising HTTP 400 |
| MODIFY | [diet_plan_service.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/services/diet_plan_service.py) | Import swapped to new schema |
| MODIFY | [meal_plan.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/routers/meal_plan.py) | TDEE now uses stored `patient.tdee` with fallback; unused top-level import removed |
| DELETE | [app/models/diet_plan.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/models/diet_plan.py) | Legacy file deleted; verified zero remaining imports ✅ |

### Key Logic Changes

#### Plan Regeneration (diet_plans.py)
```diff
 existing_plan = await diet_plan_service.get_diet_plan(...)
 if existing_plan:
-    raise HTTPException(status_code=400, detail="Diet plan already exists...")
+    # Delete old plan so a fresh one can be generated
+    await diet_plan_service.delete_diet_plan(...)
```

#### Stored TDEE (meal_plan.py)
```diff
-bmr = calculate_bmr(...)
-total_calories = calculate_tdee(bmr, current_user.activity_level)
+if current_user.tdee:
+    total_calories = float(current_user.tdee)
+else:
+    # fallback to on-the-fly calculation with warning log
+    ...
```

---

## Verification

| Check | Result |
|-------|--------|
| Alembic migration generated cleanly | ✅ No GIN index false positives |
| Alembic migration applied | ✅ `upgrade head` succeeded |
| `from ..models.diet_plan` search | ✅ Zero results |
| `from app.models.diet_plan` search | ✅ Zero results |

## Files Summary

| Status | Count | Files |
|--------|-------|-------|
| Created | 1 | [app/schemas/diet_plan.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/schemas/diet_plan.py) |
| Modified | 5 | [db_models.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/models/db_models.py), [progress_service.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/services/progress_service.py), [progress.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/routers/progress.py), [diet_plans.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/routers/diet_plans.py), [diet_plan_service.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/services/diet_plan_service.py), [meal_plan.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/routers/meal_plan.py) |
| Deleted | 1 | [app/models/diet_plan.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/models/diet_plan.py) |
| Migration | 1 | [861b9d58abdf_add_calorie_adjustment_to_progress_logs.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/alembic/versions/861b9d58abdf_add_calorie_adjustment_to_progress_logs.py) |

> [!NOTE]
> All Pyre lint errors in the IDE are pre-existing project-wide "could not find import" issues caused by virtual environment configuration — not introduced by these changes.
