# MITYAHAR — Web Dashboard Design System
> Covers: Doctor Dashboard + Admin Dashboard (Next.js 15)
> Scope: Web only. Phone/Expo design handled separately.
> Status: Design architecture v1 — ready for implementation in Sprint 3 & 4

---

## 1. Design Philosophy

Your original design (from doctor.md and admin.md) is **functionally complete and logically correct** — every screen is there, every user flow is mapped. What it's missing is a **visual identity that makes a doctor trust it with clinical work daily.**

The goal is this: a doctor who opens this dashboard at 8am should feel the same way they feel opening Notion or Linear — **calm, in control, efficient**. Not like they opened a hospital management system from 2015.

Three principles drive every decision below:

**1. Clinical clarity over decorative richness.**
Healthcare professionals make decisions from dashboards. Dense data must be scannable in under 3 seconds. Every color, every font size, every chart exists to communicate information — not to fill space.

**2. Trust through restraint.**
Doctors are skeptical of flashy software. Conservative palette, generous whitespace, precise typography = credibility. The design should look like a tool built by people who understand medicine, not a startup trying to look "fresh."

**3. Indian-product identity without kitsch.**
Mityahar is an Indian product serving Indian dieticians with Indian food data. This does not mean saffron gradients and rangoli patterns. It means the warmth of the palette, the completeness of the Indian food names on screen, and the regional context embedded in the UI all feel native — not like a Western health app with Hindi text pasted on.

---

## 2. Color System

### Brand Palette — "Verdant"
Inspired by the color of fresh curry leaves, raw coriander, and the green of Ayurvedic medicine. Not a generic "health green" — a specific, saturated, Indian-vegetation green.

```
Primary (Brand Green)
  --brand-600:  #1E7C45     ← Primary buttons, active sidebar, links
  --brand-500:  #23924F     ← Hover states
  --brand-400:  #34B164     ← Success indicators, progress bars
  --brand-100:  #DCFCE7     ← Light backgrounds, selected rows
  --brand-50:   #F0FDF4     ← Subtle page backgrounds, card tints

Neutral (Slate — not pure grey, slightly warm)
  --slate-950:  #0C1117     ← Dark mode background (if added later)
  --slate-900:  #111827     ← Primary text
  --slate-700:  #374151     ← Secondary text, labels
  --slate-500:  #6B7280     ← Placeholder, disabled
  --slate-300:  #D1D5DB     ← Borders, dividers
  --slate-100:  #F3F4F6     ← Table row hover, subtle backgrounds
  --slate-50:   #F9FAFB     ← Page background

Semantic Colors (status communication — non-negotiable consistency)
  --red-600:    #DC2626     ← Danger, errors, critical alerts
  --red-50:     #FEF2F2     ← Error background
  --amber-500:  #F59E0B     ← Warning, expiring soon, pending
  --amber-50:   #FFFBEB     ← Warning background
  --blue-600:   #2563EB     ← Informational, links, neutral actions
  --blue-50:    #EFF6FF     ← Info background
  
Chart Colors (for Recharts — consistent set, never random)
  --chart-1:    #1E7C45     ← Primary metric (weight, calories)
  --chart-2:    #2563EB     ← Secondary metric (water, steps)
  --chart-3:    #F59E0B     ← Tertiary metric (adherence)
  --chart-4:    #9333EA     ← Quaternary (if needed)
  --chart-muted:#D1D5DB     ← Empty/unfilled portions
```

### What to avoid
- ❌ Pure white (#FFFFFF) backgrounds — use `--slate-50` instead, reduces eye strain for long sessions
- ❌ Multiple greens (lime, teal, sage all at once) — stick to your one brand green family
- ❌ Red for anything that isn't actually an error — use amber for warnings
- ❌ Gradients on interactive elements — gradient buttons look like 2018 fitness apps

---

## 3. Typography

### Font Stack
```
Heading font:   "Inter" (Google Fonts — already in shadcn/ui default)
Body font:      "Inter"
Mono font:      "JetBrains Mono" or "Fira Code" (for codes, IDs, timestamps)

Why Inter: It is the industry standard for SaaS dashboards (Linear, Vercel, Notion, 
           Supabase all use it). It is engineered for screen legibility at all sizes.
           Absolutely do not use a serif or display font for a clinical dashboard.
```

### Type Scale (Tailwind classes)
```
Page Title:       text-2xl font-semibold tracking-tight   (24px, -0.5px)
Section Heading:  text-lg font-semibold                   (18px)
Card Title:       text-base font-medium                   (16px)
Body / Label:     text-sm font-normal                     (14px)  ← DEFAULT
Secondary text:   text-xs text-slate-500                  (12px)
Stat number:      text-3xl font-bold tabular-nums         (30px)
Table header:     text-xs font-medium uppercase tracking-wide text-slate-500
Code / ID:        font-mono text-sm
```

### Typography Rules
1. **One font weight for emphasis** — semibold (600). Never bold + italic + underline together.
2. **Tabular numbers everywhere** — `font-variant-numeric: tabular-nums` on all numbers in tables and stat cards. This stops numbers jumping when data refreshes.
3. **Line height 1.5 for body, 1.2 for headings** — standard shadcn/ui defaults handle this.
4. **No centered body text** — left-align everything except modal headlines and empty states.

---

## 4. Layout Architecture

### The Shell (applies to both Doctor and Admin dashboards)

```
┌──────────────────────────────────────────────────────────────┐
│  SIDEBAR (240px fixed, collapsible to 64px icon-only)        │
│  ┌──────────────────────────────────────────────────────────┐│
│  │ Logo + wordmark (top)                                    ││
│  │                                                          ││
│  │ [NAV SECTION 1 — PRIMARY]                                ││
│  │  icon + label  ← 44px min height per item               ││
│  │  icon + label                                            ││
│  │  icon + label                                            ││
│  │                                                          ││
│  │ [NAV SECTION 2 — SECONDARY]                              ││
│  │  icon + label                                            ││
│  │                                                          ││
│  │ BOTTOM (pinned)                                          ││
│  │  Doctor avatar + name + role badge                       ││
│  │  Settings link                                           ││
│  │  Logout link                                             ││
│  └──────────────────────────────────────────────────────────┘│
│                                                              │
│  MAIN AREA (fluid, fills remaining width)                    │
│  ┌──────────────────────────────────────────────────────────┐│
│  │ TOP BAR (56px, sticky)                                   ││
│  │  Breadcrumb     [search]    [notif bell]  [avatar]       ││
│  ├──────────────────────────────────────────────────────────┤│
│  │                                                          ││
│  │ PAGE CONTENT (padding: 24px)                             ││
│  │  Page title + subtitle                                   ││
│  │  [Action buttons — right aligned]                        ││
│  │                                                          ││
│  │  Content area (grid/flex)                                ││
│  │                                                          ││
│  └──────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

### Sidebar Behavior
- **Default state:** 240px wide, icon + text label visible
- **Collapsed state:** 64px wide, icon only, tooltip on hover shows label
- **Active item:** Brand green left border (3px) + `--brand-100` background
- **Hover state:** `--slate-100` background, no border
- **Sidebar background:** White (`#FFFFFF`) — NOT dark. Your users are clinical professionals using this in bright offices. Dark sidebars are trendy but reduce legibility for data-heavy applications.
- **Collapse toggle:** Arrow button at bottom of sidebar, persists state in localStorage

### Top Bar
- Height: 56px, `border-bottom: 1px solid --slate-200`, background white, `position: sticky top-0 z-50`
- Left: Breadcrumb (Page > Sub-page)
- Center: Global search (cmd+K opens command palette — implement with `cmdk` library)
- Right: Notification bell (with unread badge) → Avatar (click → dropdown: Profile, Settings, Logout)

### Content Grid
```
Dashboard pages:    CSS Grid — 12-column, 24px gap, 24px page padding
Patient detail:     Left panel (320px, patient meta) + Right panel (fluid, tabs)
Tables:             Full width, 16px cell padding, sticky header
Forms:              Max-width 640px, centered in content area
Modals:             Max-width 520px (sm), 640px (md), 768px (lg) — centered overlay
```

---

## 5. Component Patterns

### Stat Cards (Dashboard overview row)
```
Design:
  - White background, 1px border (#E5E7EB), 8px border-radius, 20px padding
  - Icon top-left (24px, brand-colored, inside a 40px brand-50 circle)
  - Large number (text-3xl font-bold tabular-nums) 
  - Label below (text-sm text-slate-500)
  - Delta/trend (optional): green arrow up or red arrow down, text-xs

Avoid:
  - Colored card backgrounds (blue card, green card etc.) — looks like a startup template
  - Shadows heavier than shadow-sm
  - Cards with too much content — one number, one label, one trend. That's it.
```

### Data Tables
```
Design:
  - No outer card border — table sits directly on page background
  - Thead: sticky, slate-50 background, text-xs uppercase tracking-wide text-slate-500
  - Row height: 52px (comfortable for clinical data reading)
  - Row hover: slate-50 background
  - Selected row: brand-50 background
  - Status badges: use colored pill badges NOT colored table rows
  - Pagination: simple prev/next + page number — no complex paginator
  - Empty state: centered illustration + message + CTA button

Status badge system (consistent across all tables):
  Active:    brand-100 bg + brand-700 text
  Inactive:  slate-100 bg + slate-600 text
  Pending:   amber-50 bg + amber-700 text
  Expired:   red-50 bg + red-600 text
  Approved:  brand-100 bg + brand-700 text
  Rejected:  red-50 bg + red-600 text
```

### Patient Cards (in list views)
```
Not a table row — a card layout for the patient list is WRONG.
Use a table. Doctors need to scan 20+ patients in one view.
Cards are better for 4-6 items max. Tables scale to 200+ rows.
```

### Charts (Recharts)
```
Weight chart:    LineChart, area fill (--chart-1 at 20% opacity), no dots except on hover
Adherence:       RadialBarChart or simple percentage ring (shadcn Progress component)
Weekly macros:   BarChart, stacked (protein/carbs/fat), single color per macro
Water/steps:     BarChart, single color, target line overlay
Calorie trend:   AreaChart, current vs target as two lines

All charts:
  - No chart titles inside the chart — title is the card heading above it
  - Tooltip: rounded-lg shadow-lg border, shows exact value + date
  - Grid lines: horizontal only, dashed, --slate-200 color
  - Axis labels: text-xs text-slate-500
  - Animation: 600ms ease-out on mount, no continuous animations
  - Responsive: ResponsiveContainer width="100%" height={240} is the standard
```

### Forms
```
Input fields:     h-10 (40px), rounded-md, border border-slate-300, 
                  focus:ring-2 focus:ring-brand-500 focus:border-transparent
Labels:           text-sm font-medium text-slate-700, mb-1.5
Helper text:      text-xs text-slate-500, mt-1.5
Error state:      border-red-500 + red-50 bg + red-600 text below field
Required marker:  Red asterisk after label — <span className="text-red-500 ml-0.5">*</span>
```

### Buttons
```
Primary:    bg-brand-600 text-white hover:bg-brand-700  (main CTAs)
Secondary:  border border-slate-300 bg-white text-slate-700 hover:bg-slate-50
Danger:     bg-red-600 text-white hover:bg-red-700  (delete, deactivate)
Ghost:      no border, no bg, text-slate-600 hover:bg-slate-100
Link:       text-brand-600 hover:underline (inline links only)

Height:     h-10 (default), h-9 (compact), h-8 (xs in table rows)
Icon+text:  icon left, 8px gap (use lucide-react icons, size=16)
Loading:    Replace icon with Loader2 (spinning), disable button
```

---

## 6. Doctor Dashboard — Redesigned Screen Architecture

### What to CHANGE from your current design

**Change 1: Sidebar — Remove "Codes & Billing" from sidebar**
Doctors think of billing as admin overhead, not a daily task. Move it into Profile/Settings. Keep the sidebar to 5 items max — this is what modern SaaS uses (Notion, Linear, Vercel all have ≤6 primary nav items).

```
Revised Doctor Sidebar:
  MAIN
  [ LayoutDashboard ]  Overview
  [ Users ]            Patients
  [ Bell ]             Requests       ← with unread badge
  [ ChefHat ]          Recipes
  
  ACCOUNT (pinned bottom)
  [ Settings ]         Settings       ← Billing + codes live here
  [ LogOut ]           Logout
  
  Avatar + "Dr. [Name]" + "Dietician" badge
```

**Change 2: Dashboard — "Needs Attention" panel as priority #1**
Your current design buries it below 4 stat cards. Invert this. The doctor logs in to handle patients who need action — put that front and center.

```
Revised Doctor Dashboard Layout:
┌────────────────────────────────────────────────────────┐
│ Good morning, Dr. Ashok    Monday, Feb 25              │
├──────────────┬──────────────────────────────────────── │
│ STAT CARDS (3, smaller)  |  QUICK ACTIONS              │
│ Active / Pending / Codes  |  [+ Accept Request]        │
│                           |  [Generate Codes]          │
├───────────────────────────┴────────────────────────── ─│
│ NEEDS ATTENTION (priority panel, left 60%)             │
│ Tab: [No Activity (3)] [Expiring Soon (5)]             │
│ ┌─────────────────────────────────────────────────┐   │
│ │ 🔴 Radha Sharma    No log in 4 days   [View →]  │   │
│ │ 🔴 Meena Joshi     No log in 6 days   [View →]  │   │
│ │ 🟡 Suresh Kumar    Expires in 5 days  [View →]  │   │
│ └─────────────────────────────────────────────────┘   │
│                                                        │
│ PENDING REQUESTS (right 40%, card list)               │
│ ┌──────────────────────────────────────────────────┐  │
│ │ Anjali Verma • Feb 24            [Accept][Reject]│  │
│ │ Rohit Patel  • Feb 23            [Accept][Reject]│  │
│ └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

**Change 3: Patient Detail — Tabbed layout is correct, but improve the tab content**

Your original design had 5 tabs. Keep them but rename and restructure:

```
[ Profile ]  [ Plan ]  [ Logs ]  [ Progress ]  [ Notes ]
                              ↑
                    Rename "Logs" to "Activity" — 
                    it contains meal logs + water + steps,
                    not just "logs" (too technical)
```

Patient detail page header — add a persistent "patient health snapshot" bar that shows across ALL tabs:
```
┌──────────────────────────────────────────────────────────┐
│ ← Patients    Radha Sharma                               │
│ Active · Expires Mar 31 · 34F · BMI 28.4 · TDEE 2090   │
│ Conditions: PCOS, Thyroid    Allergies: Dairy           │
│ Joined Jan 15 · Adherence this week: 43% 🔴             │
└──────────────────────────────────────────────────────────┘
```
This means the doctor never has to switch to Profile tab just to remember the patient's context while reading logs. The snapshot persists.

**Change 4: Meal Plan tab — Doctor override UX**

Your current design has Edit / Swap / Note buttons per meal slot. This is functionally correct but visually noisy. Use a cleaner pattern:

```
Instead of 3 buttons per meal:
  Meal slot is a card — hover reveals a single "•••" (more) menu
  Clicking it opens: Edit | Swap | Add Note | Restore Default
  
Non-hover state shows ONLY the meal name + calories + any existing doctor note
This reduces visual noise by ~60% while keeping all functionality accessible.
```

**Change 5: Requests page — Show patient context, not just name**

Your current design shows name + date + buttons. A doctor approving a request blind is risky. Add:
```
Each request card shows:
  Name · Age · Email · Phone
  "Requested Feb 24"
  [Health Goals summary if submitted]: "Weight loss, manages PCOD"
  
  [ Accept (uses 1 code) ]  [ Reject ]
  Codes remaining: 8          [Optional rejection note field, inline]
```

---

## 7. Admin Dashboard — Redesigned Screen Architecture

### What to CHANGE from your current design

**Change 1: Admin sidebar — Add "Platform" section**
Your original sidebar mixes operational and strategic items. Separate them:

```
Revised Admin Sidebar:
  OVERVIEW
  [ LayoutDashboard ]  Overview
  
  PLATFORM
  [ Stethoscope ]      Doctors
  [ Users ]            Patients
  [ Utensils ]         Food Database
  
  BILLING
  [ CreditCard ]       Codes & Billing
  
  AUDIT
  [ ScrollText ]       Audit Logs
  
  ACCOUNT (pinned bottom)
  [ Settings ]         Settings
  [ LogOut ]           Logout
```

**Change 2: Admin Overview — Lead with revenue, not just counts**

Admins are business operators. The current design shows 5 numbers of equal visual weight. Apply visual hierarchy: Revenue is the headline, everything else is supporting.

```
Revised Admin Overview:
┌────────────────────────────────────────────────────────┐
│ March 2026 · Admin Dashboard                           │
├─────────────────────────────┬──────────────────────────│
│ REVENUE HEADLINE            │ PLATFORM HEALTH          │
│ ₹61,750 this month         │ 8 doctors  (6 active)    │
│ ↑ 12% vs February          │ 312 patients (247 active)│
│                             │ 93% subscription renewal │
├─────────────────────────────┴──────────────────────────│
│ ALERTS (only if something needs action)                │
│ ⚠️  Dr. Mehta billing overdue — [Mark Paid]            │
│ ⚠️  3 food items pending approval — [Review]           │
│ ⚠️  Dr. Sonal has 2 codes left — [Generate]            │
├────────────────────────────────────────────────────────│
│ DOCTOR PERFORMANCE TABLE                               │
│ Doctor        Active Pts  Revenue    Renewal    Action │
│ Dr. Ashok     24          ₹6,000     ✅ Paid    [View] │
│ Dr. Priya     18          ₹4,500     ✅ Paid    [View] │
│ Dr. Ravi      31          ₹7,750     ⚠️ Pending [View] │
└────────────────────────────────────────────────────────┘
```

**Change 3: Billing page — Split into "Codes" and "Billing" sub-sections**

These are two different mental models for the admin. "I need to generate codes for Dr. Ashok" is completely different from "I need to check if Dr. Ashok has paid this month." Don't mix them on one page.

```
Codes & Billing page has two tabs:
  Tab 1: Subscriptions (billing — who has paid, who hasn't)
  Tab 2: Activation Codes (code management — generate, view, revoke)
```

**Change 4: Food Database — Add cleaner approval workflow**

Your original shows a flat list. A doctor-submitted recipe that needs approval should stand out more clearly:

```
Food Database tabs:
  [ All (6,871) ]  [ Pending Approval (4) ]  [ Rejected (12) ]
  
When "Pending Approval" tab has items, show a red badge on the tab.
Each pending item shows:
  - Recipe name + submitted by Dr. [X] on [date]
  - Full nutrition breakdown fetched from Edamam (if available)
  - Side-by-side: [Approve] (green) [Reject with note] (red)
  
Admin should be able to approve/reject inline without opening a detail page.
```

---

## 8. UX Patterns Your Current Design Is Missing

These are patterns that modern SaaS dashboards use that your wireframes don't include yet.

### 1. Command Palette (cmd+K / ctrl+K)
A keyboard-triggered search that lets doctors jump to any patient, any screen, any action without using the sidebar. Essential for power users.
```
Type "Radha" → shows "Radha Sharma — Patient" → press Enter → opens patient detail
Type "codes" → shows "Generate Subscription Codes" → opens codes panel
Use: cmdk library (shadcn/ui has a built-in Command component)
```

### 2. Empty States — never show a blank page
Every table, every chart, every list needs a designed empty state.
```
Patient list (no patients yet):
  [Illustration of doctor + dotted circle]
  "No patients yet"
  "Accept your first patient request to get started"
  [ View Pending Requests → ]

Progress chart (no data logged):
  "Radha hasn't logged any weight data yet."
  (No CTA — doctor can't do anything about this, just inform)
```

### 3. Optimistic UI on critical doctor actions
When a doctor taps "Accept" on a patient request, the row should visually change immediately — don't wait for the API response to complete before updating the UI. Use TanStack Query's `onMutate` for this.

### 4. Notification system (in-app)
The bell icon in the top bar should show:
```
[ New patient request — Anjali Verma — 2 hours ago ]
[ Radha Sharma hasn't logged in 5 days ]
[ Your codes are low (2 remaining) ]
```
These map exactly to the backend data you already have. No new backend work needed — just TanStack Query polling every 5 minutes on `/doctor/dashboard`.

### 5. Confirmation dialogs for destructive actions
"Remove Patient," "Reject Request," "Delete Food Item" — these all need a confirmation modal before execution.
```
Modal: "Remove Radha Sharma from your patient list?"
"This will disconnect her from your account. Her data won't be deleted."
[ Cancel ]  [ Remove Patient ]  ← red button
```

### 6. Skeleton loaders — never show spinners
When a table is loading, show skeleton rows (gray animated placeholders matching the table structure). This feels faster than a spinner and prevents layout shift.
shadcn/ui has a `Skeleton` component — use it everywhere.

### 7. Responsive table → card fallback at smaller breakpoints
If a doctor opens the dashboard on a smaller laptop (1280px wide), the patient table should still work. Use a responsive strategy:
- ≥ 1280px: Full table with all columns
- 1024px–1279px: Hide the "Adherence" column
- < 1024px: Switch to patient cards layout (3 cards per row)

---

## 9. Page-by-Page Implementation Priority

Build these in this exact order. Each is a prerequisite for the next.

### Doctor Dashboard (Sprint 3)
```
Phase A — Auth shell (do this first, everything else depends on it)
  1. Login page (clean centered card, email + password, MFA flow)
  2. Protected layout shell (sidebar + topbar + outlet)
  3. Auth store (Zustand) + Axios instance with cookie handling

Phase B — Core screens
  4. Overview/Dashboard (stat cards + attention panel + requests)
  5. Patient List (table with search + filter)
  6. Patient Detail page (shell with tabs — placeholder content in each tab)

Phase C — Patient detail tabs (fill in one by one)
  7. Profile tab
  8. Plan tab (read-only view first, edit later)
  9. Activity tab (meal log table)
  10. Progress tab (Recharts — weight + water + steps)
  11. Notes tab (list + add form)

Phase D — Secondary screens
  12. Requests page
  13. Subscription codes page (generate + list)
  14. Recipe browser
  15. Add recipe form
  16. Settings / Profile page (including MFA setup)
```

### Admin Dashboard (Sprint 4)
```
Phase A — Auth shell (same pattern as doctor)
Phase B — Overview + Doctors list + Doctor detail
Phase C — Food Database (list + approval workflow)
Phase D — Codes & Billing (split tabs)
Phase E — Audit Logs (table + filters)
Phase F — Patient management (subscription override + DPDP erasure)
```

---

## 10. Token & Variable Reference (Tailwind CSS v4 config)

```css
/* In your globals.css — Tailwind v4 uses CSS variables natively */
@layer base {
  :root {
    /* Brand */
    --brand-50:  240 253 244;   /* Use as: bg-[rgb(var(--brand-50))] */
    --brand-100: 220 252 231;
    --brand-400: 52  177 100;
    --brand-500: 35  146 79;
    --brand-600: 30  124 69;
    --brand-700: 21  128 61;
    
    /* Layout */
    --sidebar-width: 240px;
    --sidebar-collapsed-width: 64px;
    --topbar-height: 56px;
    --content-padding: 24px;
    
    /* Radius */
    --radius-sm: 6px;
    --radius-md: 8px;
    --radius-lg: 12px;
    --radius-xl: 16px;
    
    /* Shadows */
    --shadow-card: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);
    --shadow-modal: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);
  }
}
```

---

## 11. What NOT to Build (design anti-patterns to avoid)

Based on healthcare SaaS research and the Mityahar use case:

| Anti-pattern | Why to avoid |
|---|---|
| Dark mode (at launch) | Adds 30% to development time. Doctors in clinics use light mode. Defer to v2 |
| Animated background gradients | Looks like a gym app, not a clinical tool |
| Floating action buttons (FABs) | Mobile pattern. Doesn't belong in a desktop web dashboard |
| Inline editing everywhere | Doctor plan editing is deliberate — use a modal/drawer, not inline edit which causes accidental edits |
| Infinite scroll on patient list | Doctors need pagination. They reference "Page 2, Row 3." Infinite scroll breaks that mental model |
| Colored stat card backgrounds | One color for each number makes it look like a mobile app. Use white cards with colored icons only |
| Toast notifications for errors | Errors need to be persistent, not toast (which disappears). Use inline error states |
| Toast for success only | ✅ Toast is correct for success actions ("Patient accepted", "Plan saved") |
| Data tables with row checkboxes if no bulk action | Checkbox columns that don't do anything confuse users |
| Pie charts for proportions | Use a stacked bar or separate bars. Pie charts are hard to read accurately in data-dense contexts |

---

## 12. Reference Products to Study (not copy)

Spend 20 minutes in each of these — understand WHY they made their specific layout choices:

1. **Linear.app** — Perfect sidebar architecture, stat display, issue list patterns
2. **Vercel Dashboard** — Clean deployment log, table design, status badges
3. **Notion** — Command palette (cmd+K), empty states, typography hierarchy  
4. **Cal.com** — Open source, healthcare adjacent, good form design patterns
5. **Lemon Squeezy** (Revenue dashboard) — How to display financial data cleanly
6. **Supabase Dashboard** — How to do data tables at scale, admin panel patterns

Dribbble searches that will be useful:
- "Healthcare SaaS dashboard 2025"
- "Medical CRM dark mode"
- "Patient management table UI"
- "Nutrition tracker web app dashboard"

---

## Summary of Changes vs Your Original Design

| Area | Original Design | Recommended Change |
|---|---|---|
| Sidebar items | 7 items (doctor) / 8 items (admin) | 4-5 primary + account group |
| Dashboard priority | Stats first, attention panel buried | Attention panel = primary, stats = secondary |
| Patient snapshot | Only visible on Profile tab | Persistent header across ALL patient tabs |
| Meal slot actions | 3 buttons always visible | Hidden behind ••• menu, revealed on hover |
| Food approval | Flat list, needs detail page to approve | Inline approve/reject on Pending tab |
| Admin billing | Single page mixing codes + billing | Split into 2 tabs (Subscriptions / Codes) |
| Empty states | Not designed | Every table and list needs a designed empty state |
| Loading states | Implied spinner | Skeleton loaders everywhere |
| Request approval | Name + date + buttons | Full patient context card before approve |
| Color system | Not specified | Verdant green + warm slate defined above |
| Typography | Not specified | Inter throughout, defined scale above |

The overall direction: your wireframes captured the right information architecture. What this document adds is the visual execution layer — how that information is presented in a way that a doctor trusts and uses daily without friction.
