# Three-Role Auth + Middleware — Walkthrough

## Changes Made

| File | Action | Summary |
|------|--------|---------|
| [app/core/security.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/core/security.py) | Rewritten | Added [get_current_patient](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/core/security.py#99-134) (w/ subscription 402 check), [get_current_doctor](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/core/security.py#136-161), [get_current_admin](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/core/security.py#163-188). JWT always includes `sub`/`role`/`user_type`/`exp`/`iat`/`nbf` |
| [app/core/middleware.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/core/middleware.py) | **New** | [SubscriptionCheckMiddleware](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/core/middleware.py#61-140) — blocks expired patients on `/meal-plan`, `/progress`, `/diet-plans`; skips `/auth`. [DoctorIsolationMiddleware](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/core/middleware.py#146-197) — restricts `/doctor/*` to doctors, injects `request.state.doctor_id` |
| [app/services/user_service.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/services/user_service.py) | Modified | Removed inline `get_current_user` impl. Added `get_current_user = get_current_patient` alias for backward compat (5 routers import it) |
| [app/routers/auth.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/routers/auth.py) | Modified | Added `POST /api/v1/auth/doctor/login` — authenticates against `doctors` table, returns JWT with `role=doctor` |
| [app/main.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/main.py) | Modified | Wired both middleware layers: [SubscriptionCheckMiddleware](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/core/middleware.py#61-140) then [DoctorIsolationMiddleware](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/core/middleware.py#146-197) |

## Silent Bug Protections

- **Subscription middleware skips `/auth/*`** — login/register never blocked
- **Malformed JWT → 401** in both middleware layers (never 500)
- **`get_current_user` alias** preserved — [diet_plans.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/routers/diet_plans.py), [progress.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/crud/progress.py), [users.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/routers/users.py), [meal_plan.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/routers/meal_plan.py), [calculations.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/tests/test_calculations.py) all continue to work
- **`request.state.doctor_id`** set before route handler runs (in middleware [dispatch](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/core/middleware.py#68-140))

## Verification

- `uvicorn app.main:app --port 8001` → `Application startup complete`, zero errors
