# MITYAHAR — SPRINT 3 HANDOFF
> Generated: 2026-03-08 | Backend complete (95/95 tests) | Next: Doctor Dashboard (Next.js 15)

## How to use this file
Paste the entire contents as your first message in the Sprint 3 chat.
Claude will reconstruct full context and be ready to scaffold the Doctor Dashboard immediately.

---

## Project Overview

**Name:** Mityahar — AI-powered Indian diet planning app  
**Backend:** FastAPI + PostgreSQL (SQLAlchemy 2.0 async + asyncpg) + Alembic — **COMPLETE**  
**Backend Location:** `C:\Users\Lenovo\Desktop\Code\2026\Nutria\Mitihar_dietician`  
**Backend URL (local):** `http://localhost:8000/api/v1`  
**OpenAPI spec:** `http://localhost:8000/openapi.json`  
**Backend start:** `venv\Scripts\uvicorn app.main:app --reload --port 8000`  
**Backend tests:** 95/95 passing (run `venv\Scripts\python scripts\test_all_endpoints.py`)

---

## Frontend Architecture Decision (finalised 2026-03-08)

### Monorepo
```
mityahar-frontend/           ← create this at same level as Mitihar_dietician
├── apps/
│   ├── admin/               # Next.js 15 App Router — port 3002
│   ├── doctor/              # Next.js 15 App Router — port 3001
│   └── patient/             # Expo SDK 54 (New Architecture)
├── packages/
│   ├── api-client/          # Auto-generated TS client from /openapi.json
│   ├── types/               # Shared Zod schemas + TypeScript interfaces
│   └── ui/                  # Shared shadcn/ui primitives (web only)
├── turbo.json
└── pnpm-workspace.yaml
```

### Doctor Dashboard stack (Sprint 3 — build this first)
| Layer | Choice |
|---|---|
| Framework | Next.js 15 App Router |
| Language | TypeScript strict |
| Styling | Tailwind CSS v4 + shadcn/ui |
| Server state | TanStack Query v5 |
| Client state | Zustand v5 |
| Forms | React Hook Form + Zod |
| Charts | Recharts |
| HTTP | Axios (with interceptor for silent token refresh) |
| Auth storage | Access token in Zustand memory + refresh token in HttpOnly cookie |

### Token security model (already implemented in backend)
```
Doctor Login:
  POST /api/v1/auth/doctor/login → {access_token, refresh_token, token_type}
  Backend ALSO sets:  Set-Cookie: refresh_token=<value>; HttpOnly; SameSite=Lax; Path=/api/v1/auth

Frontend:
  access_token  → Zustand store (in-memory only, lost on tab close)
  refresh_token → lives in HttpOnly cookie (set by backend, inaccessible to JS)

On 401 from any API call:
  Axios interceptor → POST /api/v1/auth/refresh (cookie sent automatically by browser)
  → new access_token → retry original request → user never sees a flash
```

---

## Backend — Complete API Reference (Doctor-relevant endpoints)

### Auth (`/api/v1/auth/`)
```
POST  /auth/doctor/login          form: username, password
                                   → {access_token, refresh_token, token_type}
                                      OR {mfa_required: true, partial_token}  if MFA enabled
POST  /auth/doctor/mfa-login      body: {partial_token, totp_code}
                                   → {access_token, refresh_token, token_type}
POST  /auth/doctor/mfa-setup      doctor_token → {totp_uri}  (QR code URI)
POST  /auth/doctor/mfa-confirm    body: {totp_code} → enables MFA
POST  /auth/doctor/mfa-disable    body: {totp_code} → disables MFA
POST  /auth/refresh               body: {refresh_token} → {access_token}
```

### Doctor Dashboard (`/api/v1/doctor/`) — all require doctor JWT
```
GET   /doctor/dashboard
      → {total_patients, active_patients, pending_requests, plans_generated_this_week,
         inactive_patients: [{id,name,last_log_date}], expiring_soon: [{id,name,sub_end_date}]}

GET   /doctor/patients?page=1&page_size=20
      → {patients: [...], total: int}

GET   /doctor/patients/{patient_id}
      → full patient profile (all 38 fields)

GET   /doctor/patients/{patient_id}/plan
      → active Recommendation with meals JSONB

PUT   /doctor/patients/{patient_id}/plan
      body: {doctor_notes: str, meals: null|array}
      → updated plan (meals=null keeps existing meals, only updates notes)

POST  /doctor/patients/{patient_id}/plan/notes
      body: {meal_date: "YYYY-MM-DD", meal_type: str, note: str}
      → injects note into specific meal slot

GET   /doctor/patients/{patient_id}/logs?days=7
      → [MealLog, ...]

GET   /doctor/patients/{patient_id}/progress?days=30
      → {weight: [...], water: [...], steps: [...]}

POST  /doctor/patients/{patient_id}/notes
      body: {content: str, note_type: "general"|"dietary"|"medical"|"progress", is_private: bool}
      → ClinicalNote (201)

GET   /doctor/patients/{patient_id}/notes
      → [ClinicalNote, ...]  (only this doctor's notes)

DELETE /doctor/patients/{patient_id}
      → patient becomes standalone + inactive (account NOT deleted)

GET   /doctor/requests
      → [PatientRequest with patient details, ...]

POST  /doctor/requests/{id}/accept
      → patient.doctor_id set, sub_status=active

POST  /doctor/requests/{id}/reject
      body: {rejection_note: str}

POST  /doctor/subscription-codes
      body: {count: int, expires_in_days: int}
      → [code_string, ...]

GET   /doctor/subscription-codes
      → [{code, is_used, used_by_patient_id, used_at, expires_at}, ...]

GET   /doctor/recipes?diet_type=&meal_time=&search=&page=1&page_size=20
      → [FoodItem, ...]

POST  /doctor/recipes
      body: {recipe_name, slot_type, cal_per_serving, protein_per_serving,
             carbs_per_serving, fat_per_serving, fiber_per_serving, diet_type,
             meal_time_tags, plan_type_tags, ingredients, region_tags}
      → FoodItem (201, source="doctor", is_verified=false)

POST  /doctor/recipes/{id}/assign
      body: {patient_ids: [int], meal_type: str, meal_date: "YYYY-MM-DD", note: str}
      → {updated_count: int, failed_patient_ids: [int]}
```

---

## Doctor Dashboard — 18 Screens

### Auth Screens (2)
1. **Login** — email + password form → handles MFA_REQUIRED flag → routes to MFA screen
2. **MFA Verify** — 6-digit TOTP input (only shown when mfa_required=true)

### Main App Screens (16) — all behind auth guard
3. **Dashboard / Overview** — stats cards (total patients, active, pending requests), inactive patients list, expiring subscriptions alert
4. **Patient List** — paginated table, search by name/email, status badges, click → patient detail
5. **Patient Detail** — tabbed view (Overview / Plan / Logs / Progress / Notes)
6. **Patient Overview Tab** — BMI, BMR, TDEE, allergies, medical conditions, diet type, region
7. **Patient Plan Tab** — read-only view of current meal plan + doctor can add notes per slot
8. **Patient Logs Tab** — meal log table, last 7 days, calories breakdown
9. **Patient Progress Tab** — weight chart (Recharts line), water/steps bars
10. **Patient Notes Tab** — clinical notes list + add new note form
11. **Pending Requests** — list of patients requesting connection, Accept / Reject actions
12. **Subscription Codes** — generate new codes, list existing codes with status badges
13. **Recipe Browser** — search/filter food DB, diet type + meal time filters
14. **Add Custom Recipe** — form (all FoodItem fields), submits for admin approval
15. **Override Patient Plan** — doctor replaces/annotates a patient's active plan
16. **Assign Recipe** — select a recipe → assign to patient(s) by date + meal type
17. **Profile / Settings** — doctor profile (name, specialization, clinic), MFA setup/disable
18. **MFA Setup Flow** — QR code display → enter code to confirm → success

---

## Zustand Store Design

```typescript
// useAuthStore.ts
interface AuthStore {
  accessToken: string | null
  doctor: {id: number, email: string, name: string, role: "doctor"} | null
  setTokens: (access: string) => void
  setDoctor: (doctor: Doctor) => void
  logout: () => void
}

// useUIStore.ts
interface UIStore {
  sidebarOpen: boolean
  toggleSidebar: () => void
  activePatientId: number | null
  setActivePatient: (id: number) => void
}
```

## Axios Instance

```typescript
// lib/axios.ts
const api = axios.create({ baseURL: "http://localhost:8000/api/v1", withCredentials: true })

// Request interceptor: attach access token from Zustand
api.interceptors.request.use(config => {
  const token = useAuthStore.getState().accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Response interceptor: silent refresh on 401
api.interceptors.response.use(
  res => res,
  async error => {
    if (error.response?.status === 401 && !error.config._retry) {
      error.config._retry = true
      const { data } = await axios.post("/api/v1/auth/refresh", {}, { withCredentials: true })
      useAuthStore.getState().setTokens(data.access_token)
      error.config.headers.Authorization = `Bearer ${data.access_token}`
      return api(error.config)
    }
    return Promise.reject(error)
  }
)
```

Note: `withCredentials: true` is required on all requests so the browser sends the HttpOnly refresh_token cookie automatically.

---

## TanStack Query Keys Convention

```typescript
// queryKeys.ts
export const queryKeys = {
  dashboard:     ["doctor", "dashboard"],
  patients:      (page: number) => ["doctor", "patients", page],
  patient:       (id: number) => ["doctor", "patient", id],
  patientPlan:   (id: number) => ["doctor", "patient", id, "plan"],
  patientLogs:   (id: number, days: number) => ["doctor", "patient", id, "logs", days],
  patientProg:   (id: number, days: number) => ["doctor", "patient", id, "progress", days],
  patientNotes:  (id: number) => ["doctor", "patient", id, "notes"],
  requests:      ["doctor", "requests"],
  codes:         ["doctor", "codes"],
  recipes:       (filters: object) => ["doctor", "recipes", filters],
}
```

---

## Zod Schema Examples (mirrors Pydantic)

```typescript
// schemas/patient.ts
export const OnboardingRequestSchema = z.object({
  date_of_birth: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  food_allergies: z.array(z.string()).min(1),   // "None" is valid sentinel
  health_goals: z.array(z.string()),
  meals_per_day: z.union([z.literal(3), z.literal(5)]),
  target_weight_kg: z.number().positive(),
  // ... etc
})

// schemas/recipe.ts
export const RecipeCreateSchema = z.object({
  recipe_name: z.string().min(3).max(255),
  cal_per_serving: z.number().positive(),
  diet_type: z.enum(["Vegetarian", "Eggetarian", "Non-Veg"]),
  // ... etc
})
```

---

## Working Rules — Non-Negotiable

1. **Never trust Antigravity** (currently broken) — write everything directly.
2. **Doctor isolation** — every API call on the frontend is scoped by the JWT `doctor_id` claim; the backend enforces this via DoctorIsolationMiddleware, but don't build UI that even attempts cross-doctor requests.
3. **Token storage** — access token in Zustand memory only. Never localStorage/sessionStorage. Refresh token is HttpOnly cookie (set by backend, never touched by JS).
4. **`withCredentials: true`** on every Axios request — this is what sends the HttpOnly cookie to the backend.
5. **TypeScript strict** — no `any`, no `@ts-ignore`. Generate types from OpenAPI spec, don't handwrite them.
6. **Zod everywhere** — all forms use React Hook Form + Zod resolver. No unvalidated user inputs reach the API.
7. **Each sprint gets its own chat** — don't mix Sprint 3 work with future admin/patient work.
8. **Test command (backend):** `venv\Scripts\python scripts\test_all_endpoints.py` — must stay 95/95.

---

## Backend State (exactly as of Sprint 2 completion)

### What is done and locked
- **Phase 3 Admin Backend: 23/23 ✅ COMPLETE**
- **Phase 2 Doctor Backend: 25/26** (1 optional Edamam auto-fetch remains)
- **Phase 0/1 Backend: 40/42** (FCM token storage + slot linking deferred)
- **Security: 8/12** (KMS encryption, prod CORS, security headers, DPDP cron deferred)
- **95/95 integration tests passing**

### Critical backend details for frontend
- DB: `postgresql+asyncpg://admin:mityahar_dev@localhost:5432/mityahar_db`
- All 12 ORM tables in `app/models/db_models.py` — do not modify
- Alembic: 8 migrations applied, `alembic check` clean
- `food_items`: 2,116 rows (184 verified + 1,930 unverified + 2 test)
- `meal_templates`: 180 rows (5 times × 4 regions × 3 diets × 3 plan types)
- Admin seed: `seed_admin.py` at project root (run once if DB is fresh)
- Admin login: `admin@mityahar.com` / `admin1234`

### Backend files to know (do not modify during frontend sprint)
```
app/routers/auth.py         ← doctor/admin login + MFA + HttpOnly cookie
app/routers/doctor.py       ← all 25 doctor endpoints
app/core/middleware.py      ← DoctorIsolationMiddleware (injects request.state.doctor_id)
app/core/security.py        ← JWT deps
app/models/db_models.py     ← ALL ORM models — DO NOT MODIFY
```

---

## Sprint Plan Reminder

| Sprint | Scope | Status |
|---|---|---|
| 0-2 | Full backend (all phases) | ✅ Done |
| **3** | **Doctor Dashboard — Next.js 15 (18 screens)** | 🔲 **Start here** |
| 4 | Admin Dashboard — Next.js 15 (13 screens) | 🔲 Queued |
| 5 | Patient App — Expo SDK 54 (36 screens) | 🔲 Queued |
| 6 | Phase 4 Billing (Razorpay) + Phase 5 FCM | 🔲 Queued |
| 7 | ML quality (Phase 6 improvements) | 🔲 Queued |
| 8 | Production deploy (GCP + Cloud Run + CI/CD) | 🔲 Queued |

---

## First Steps for Sprint 3 Chat

In the Sprint 3 chat, start with:
```
1. pnpm init + turbo.json at mityahar-frontend/
2. create apps/doctor with: npx create-next-app@latest doctor --typescript --tailwind --app --use-pnpm
3. install: pnpm add @tanstack/react-query zustand axios react-hook-form zod @hookform/resolvers recharts
4. install shadcn/ui: pnpm dlx shadcn@latest init
5. run: curl http://localhost:8000/openapi.json > packages/api-client/openapi.json
6. run: pnpm dlx openapi-typescript packages/api-client/openapi.json -o packages/types/api.d.ts
7. build auth pages first (Login → MFA → protected layout), verify cookie is set
8. build Dashboard screen, verify TanStack Query fetches correctly
9. build Patient List → Patient Detail screens
```
