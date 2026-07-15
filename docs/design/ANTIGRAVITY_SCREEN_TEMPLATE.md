# MITYAHAR — Antigravity Screen Build Template
> Use this template for every screen you generate from Stitch.
> Fill in the [BRACKETED] sections. Remove sections that don't apply.
> Keep it under 60 lines. Shorter prompts = less hallucination.

---

## TEMPLATE (copy this for each screen)

```
Build [SCREEN NAME] for the Mityahar [Doctor/Admin] Dashboard.

## Visual Reference
[Attach Stitch screenshot here]

## Tech Stack (non-negotiable)
- Next.js 15 App Router, TypeScript strict
- Tailwind CSS v4 + shadcn/ui components
- TanStack Query v5 for server state
- Zustand v5 (useAuthStore) for access token
- Axios instance from lib/axios.ts (has 401 interceptor + withCredentials:true)

## Design Tokens
Primary green:     #1E7C45  (brand-600)
Primary bg tint:   #F0FDF4  (brand-50)
Active nav border: 3px solid #1E7C45
Page bg:           #F9FAFB  (slate-50)
Card bg:           #FFFFFF with border border-slate-200
Heading font:      Inter, font-semibold
Body font:         Inter, font-normal text-sm
Numbers:           font-variant-numeric: tabular-nums

## Layout
Uses: /app/(dashboard)/layout.tsx (sidebar + topbar already built)
Route: /app/(dashboard)/[ROUTE]/page.tsx

## Components on This Screen
[List each component you can see in the screenshot]
Example:
- Stat card ×3 (shadcn Card, icon + number + label + trend)
- Data table (shadcn Table, sticky thead, 52px rows, skeleton on load)
- Status badge (pill: Active=brand-100/brand-700, Pending=amber-50/amber-700, Expired=red-50/red-600)
- Empty state (centered, icon + message + optional CTA)

## Data Source
API endpoint: GET /api/v1/[ENDPOINT]
TanStack Query key: [queryKeys.XXX]
Loading state: Show Skeleton rows (use shadcn Skeleton, match table structure)
Empty state: "[MESSAGE]" with [CTA or no CTA]
Error state: Show shadcn Alert variant="destructive" inline, not toast

## Actions on This Screen
[List each button/action and what it calls]
Example:
- Accept button → POST /doctor/requests/{id}/accept
  → optimistic update (remove row immediately)
  → on success: toast("Patient accepted") + invalidate queryKeys.requests
  → on error: rollback + toast error

## What NOT to do
- Do not use localStorage for any state
- Do not use colored card backgrounds (icon color only, card stays white)
- Do not show raw spinner — use Skeleton component
- Do not use inline editing — use modal/drawer for edits
- Confirmation modal required before: delete, remove patient, reject request
```

---

## FILLED EXAMPLE — Doctor Overview / Dashboard Screen

```
Build the Doctor Overview Dashboard for the Mityahar Doctor Dashboard.

## Visual Reference
[Attach Stitch screenshot of dashboard screen]

## Tech Stack (non-negotiable)
- Next.js 15 App Router, TypeScript strict
- Tailwind CSS v4 + shadcn/ui
- TanStack Query v5
- Zustand v5 (useAuthStore)
- Axios from lib/axios.ts

## Design Tokens
Primary green: #1E7C45 | Page bg: #F9FAFB | Cards: white + border-slate-200

## Layout
Route: /app/(dashboard)/overview/page.tsx
Uses existing layout.tsx shell.

## Components on This Screen
- Page header: "Good morning, Dr. [name]" + today's date (text-2xl font-semibold)
- Stat cards ×3: Active Patients / Pending Requests (with amber badge) / Codes Remaining
- Needs Attention panel (left, 60% width):
    Tabs: "No Activity ({count})" | "Expiring Soon ({count})"
    Each row: patient name + context + [View →] button
    Empty tab state: "All patients are active and logging"
- Pending Requests panel (right, 40% width):
    Each card: patient name + request date + [Accept] [Reject] buttons
    Accept shows inline "uses 1 code" helper text
    Empty state: "No pending requests"

## Data Source
API endpoint: GET /api/v1/doctor/dashboard
TanStack Query key: queryKeys.dashboard  →  ["doctor", "dashboard"]
Refetch interval: 5 minutes (refetchInterval: 5 * 60 * 1000)
Loading state: 3 skeleton stat cards + skeleton list rows

## Actions on This Screen
- [View →] on attention panel → router.push(`/patients/${id}`)
- [Accept] on request → POST /doctor/requests/{id}/accept
    optimistic: remove card immediately
    success: toast("Patient accepted") + invalidate dashboard + requests
    error: rollback card + toast error
- [Reject] on request → open shadcn Dialog (confirmation + optional note field)
    on confirm → POST /doctor/requests/{id}/reject  with {rejection_note}
    success: toast("Request rejected") + invalidate
- Stat cards are not clickable — informational only

## What NOT to do
- Do not use colored stat card backgrounds
- Do not show spinner — skeleton only
- Accept does not need confirmation dialog (low-risk)
- Reject DOES need confirmation dialog with optional note
```

---

## FILLED EXAMPLE — Patient List Screen

```
Build the Patient List screen for the Mityahar Doctor Dashboard.

## Visual Reference
[Attach Stitch screenshot]

## Tech Stack
(same as above)

## Layout
Route: /app/(dashboard)/patients/page.tsx
Page header: "My Patients" + patient count badge + [future: filter button]

## Components on This Screen
- Search input (shadcn Input, left icon = Search, debounced 300ms)
- Filter row: Status dropdown [All | Active | Expired | Pending]
- Data table:
    Columns: Name | Status | Subscription Expires | Adherence % | Action
    Row height: 52px
    Status badge: Active=brand-100/brand-700, Expired=red-50/red-600
    Adherence: colored text — ≥70% green, 40-70% amber, <40% red + 🔴 icon
    Action column: [View →] button (text, not filled)
    Sticky table header
    Skeleton: 8 placeholder rows on load
- Pagination: simple Prev / Page X of Y / Next (shadcn Pagination)
- Empty state: "No patients yet" + [View Pending Requests →] CTA

## Data Source
API: GET /api/v1/doctor/patients?page={page}&page_size=20&search={query}
TanStack Query key: queryKeys.patients(page)  →  ["doctor", "patients", page]
URL search params: sync page and search to URL (?page=2&q=radha) using nuqs library

## Actions on This Screen
- Row click OR [View →] → router.push(`/patients/${patient.id}`)
- Search input → update URL param + refetch
- Filter → update URL param + refetch
- Pagination → update URL param + scroll to top

## What NOT to do
- Do not use card layout for patients — table only
- Do not implement bulk select (no bulk actions exist in backend)
- Do not show "remove patient" on this page — only on patient detail
```

---

## FILLED EXAMPLE — Patient Detail Screen

```
Build the Patient Detail page for the Mityahar Doctor Dashboard.

## Visual Reference
[Attach Stitch screenshot]

## Layout
Route: /app/(dashboard)/patients/[id]/page.tsx
Dynamic segment: patient id from URL

## Persistent Header (shows on ALL tabs — never changes)
  ← Back to Patients    [Patient Full Name]                [Remove Patient]
  [Status badge] · Expires [date] · [Age][Gender] · BMI [x] · TDEE [x] kcal
  Conditions: [list] | Allergies: [list]
  Joined [date] · Adherence this week: [x]% [colored badge]

## Tab Structure (shadcn Tabs)
  [Profile] [Plan] [Activity] [Progress] [Notes]
  Each tab is a separate component — lazy loaded on tab switch

## Tab 1: Profile
  Two-column layout:
    Left: Personal info (name, email, phone, DOB, gender)
    Right: Clinical data (height, weight, BMI, BMR, TDEE, goals, conditions, allergies, diet)
  Read-only. No edit from doctor side.

## Tab 2: Plan
  Current active 7-day meal plan
  Day selector (Mon-Sun pill tabs)
  Each meal slot is a card:
    Meal name + calories + slot type (Breakfast/Lunch/Dinner)
    On hover: ••• menu appears (Edit | Add Note | Restore Default)
  "No active plan" empty state with [Generate Plan] note (links to patient logging plan)
  [Save Changes] button — sticky bottom bar, only shows when changes pending

## Tab 3: Activity (meal logs)
  Week navigator: ← [Feb 25–Mar 3] →
  Table: Date | Meal Type | Recommended | Actually Logged | Calories | Match
  Match column: ✅ (same item) ⚠️ (different item) ❌ (not logged)
  Adherence % for selected week shown above table

## Tab 4: Progress
  Four charts (Recharts, 240px height each, 2-column grid):
    Weight over time (LineChart + AreaChart fill, last 30 days)
    Daily calories vs TDEE target (BarChart + target line, last 14 days)
    Water intake daily (BarChart, last 14 days)
    Steps daily (BarChart, last 14 days)
  Date range selector: [7d] [14d] [30d]

## Tab 5: Notes
  List of clinical notes (newest first)
  Each note: date + note_type badge + content text
  [+ Add Note] button → opens shadcn Sheet (right drawer, not modal)
    Form: note_type (select) + content (textarea) + is_private toggle
    Submit → POST /doctor/patients/{id}/notes

## Data Sources
  Patient data:    GET /doctor/patients/{id}         queryKeys.patient(id)
  Plan:            GET /doctor/patients/{id}/plan     queryKeys.patientPlan(id)
  Activity logs:   GET /doctor/patients/{id}/logs     queryKeys.patientLogs(id, 7)
  Progress:        GET /doctor/patients/{id}/progress queryKeys.patientProg(id, 30)
  Notes:           GET /doctor/patients/{id}/notes    queryKeys.patientNotes(id)

## Destructive Action: Remove Patient
  [Remove Patient] button → shadcn AlertDialog
  Message: "Remove [name] from your patient list?"
  Subtext: "They'll become a standalone user. Their data won't be deleted."
  Confirm → DELETE /doctor/patients/{id}
  On success: toast + router.push("/patients")

## What NOT to do
- Do not load all tab data on mount — lazy load each tab's query on first tab visit
- Do not use inline editing on plan — use the ••• menu → modal/sheet
- Do not show doctor-private notes badge to anyone (these are all doctor-only)
```

---

## HOW TO USE WITH STITCH

1. Open Stitch, paste the relevant section of WEB_DESIGN_SYSTEM.md as the style context
2. Describe the screen you want: "Doctor dashboard with left sidebar, 3 stat cards, needs-attention panel, pending requests panel"
3. Iterate in Stitch until the layout, colors, and components match the design system
4. Export/screenshot the final Stitch output
5. Open a fresh Antigravity chat
6. Paste: [screenshot] + [the filled template above for that screen]
7. Do NOT paste the full WEB_DESIGN_SYSTEM.md into Antigravity — use the stripped template only

## WHY SHORTER PROMPTS TO ANTIGRAVITY
The full design system doc is 400+ lines. Antigravity reads all of it but weights 
the beginning and end heavily. Critical specs buried in the middle get lost.
The per-screen template puts ONLY what's needed for THIS screen, in order of 
importance. Result: ~60% fewer hallucinated components and correct shadcn usage.
