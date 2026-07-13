---
name: frontend-notes
description: Technical gotchas for Mityahar web dashboard and patient mobile app — loaded when touching frontend or patient-app files
paths: "{mitihar-frontend,mitihar-patient-app}/**"
---

## Web Dashboard (mitihar-frontend/apps/)

- **Patient token** stored in localStorage as `mitihar_access_token`
- **Zustand v5** — always resolves to CJS build on web (metro.config.js override in place)
- **MealConfigTab.tsx** — `patient-tabs/MealConfigTab.tsx`. Props: `{ patientId: number }`. Uses `qk.patientMealConfig(id)` for cache. Debounced recipe search (300ms). Save & Regenerate button disabled when sum ≠ 85. Invalidates `qk.patientPlan(id)` after 2s on save.
- **W3 closed (2026-06-29):** pin=sort boost confirmed (not force-inject); slot_type added to pinned/blocked dish cards in MealConfigTab.

## Patient Mobile App (mitihar-patient-app/)

- **Onboarding fields:** activity_level uses short codes (e.g. `"LA"` not `"Lightly Active"`)
- **Meal type strings** must be exact: `"Breakfast"`, `"Lunch"`, `"Dinner"` — snack meal types fully removed in Sessions 11–12
- **meals_per_day column default was 5** from original schema — corrected to 3 in Session 12 post-fix (db_models.py + progress_service fallback). All 6 existing patients migrated via direct SQL. If meal structure changes again, search for hardcoded `5` in these two files plus any onboarding UI options.
- **Zustand v5** — always resolves to CJS build on web (metro.config.js override in place)
