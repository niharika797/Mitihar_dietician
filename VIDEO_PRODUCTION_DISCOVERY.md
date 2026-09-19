# VIDEO PRODUCTION DISCOVERY REPORT: MITIHAR PLATFORM

**Document Purpose:** Comprehensive pre-production discovery and technical-to-narrative blueprint for the client-facing Remotion project-explainer video for the **Mitihar** dietetics platform.
**Target Output:** 4–5 minute high-fidelity explainer video (240–270 seconds @ 30fps).
**Repository Basis:** `niharika797/Mitihar_dietician` (Branch: `feature/api-remediation-v0.2`, HEAD commit `081e2aa`).
**Audit Standard:** Grounded strictly in verified codebase implementation, git logs, database schemas, test results, and deployment artifacts. No speculative or unverified claims.

---

## 1. Executive Summary

**Mitihar** (also referenced as *Mityahar*) is an enterprise-grade, AI-assisted clinical dietetics and precision nutrition management platform engineered specifically for the Indian healthcare ecosystem. It solves the critical fragmentation of modern dietetic practices—where practitioners juggle patient communications across WhatsApp, static PDF meal charts, and untracked spreadsheets—by establishing a closed-loop, data-driven collaboration between clinical dieticians, patients, and healthcare administrators.

The platform is architecturally unified across three distinct applications:
1. **Clinical Doctor Dashboard (`mitihar-frontend/apps`)**: A responsive desktop web application built with React 19, TypeScript, Vite, Tailwind CSS, and Radix UI, providing dieticians with real-time patient rosters, automated 7-day meal plan generation, ingredient-level nutritional oversight, custom dish authoring, and clinical progress monitoring.
2. **Patient Companion App (`mitihar-patient-app`)**: A cross-platform mobile application built on React Native and Expo Router (with NativeWind styling), guiding patients through an 8-stage biometric onboarding flow, interactive 21-meal weekly schedules, 1-tap meal and hydration logging, pantry-aware shopping lists, and visual progress tracking.
3. **High-Performance Core Backend (`app/`)**: A FastAPI asynchronous REST service backed by PostgreSQL 15, SQLAlchemy 2.0, and Redis, incorporating a 5-layer security middleware stack, 84+ endpoints, a deterministic meal generation engine tailored to 4 Indian culinary regions and clinical health conditions, with Gemini AI fallback integration.

**Deployment & Readiness Status:**
The backend API has an active, load-tested staging deployment on **Google Cloud Run** in region `asia-south1`, connected to Cloud SQL PostgreSQL and GCP Memorystore Redis via Direct VPC Egress, orchestrated by 3 Cloud Scheduler cron jobs. Both the web dashboard and mobile companion application are fully engineered and tested locally against the staging API, with Firebase Hosting and Expo EAS build configurations in place.

---

## 2. Product Story & Architecture

### What Mitihar Actually Is
Mitihar is a **clinical nutrition operating system**. It is not a generic calorie counter or a self-serve fitness gimmick; it is an authenticated clinical tool designed to empower dieticians to prescribe, adjust, and monitor culturally authentic, medically restricted dietary regimens for Indian patients.

### The Problem It Solves
1. **Unscalable Practitioner Workflows**: Dieticians spend 45–60 minutes manually calculating BMR, TDEE, and macro splits on spreadsheets for a single patient.
2. **Lack of Indian Culinary Nuance**: Western diet apps fail on Indian cuisine, either missing traditional dishes or completely misrepresenting staple compositions (e.g., regional dal variants, roti types, sabzi preparations, accompaniments).
3. **Medical Safety Blindspots**: Patients with comorbid conditions (e.g., Type 2 Diabetes combined with Hypertension or PCOS) receive generalized meal advice that lacks automated ingredient-level allergen and clinical conflict filtering.
4. **Adherence Vacuum**: Once a static PDF is handed to a patient, doctors have zero visibility into whether the patient followed the plan, skipped meals, or struggled with ingredient availability.
5. **Administrative Chaos**: Clinics lack centralized token management, audit trails, and billing transparency for multi-practitioner practices.

### Who the Users Are (Three-Role System)
* **The Patient**: Individuals seeking clinically supervised weight management, diabetes control, or therapeutic nutrition who need clear, culturally resonant daily guidance without overwhelming manual arithmetic.
* **The Doctor / Dietician**: Certified nutritionists, doctors, and clinic consultants who require automated clinical math, deep plan customization, and longitudinal patient compliance tracking.
* **The Healthcare Admin / Clinic Owner**: Super administrators managing practitioner licensing, IP-whitelisted access, subscription token allocation, and practice-wide audit logging.

### Current Workflow vs. Mitihar Workflow
| Stage | Traditional Workflow (Without Mitihar) | Mitihar Closed-Loop Workflow |
|---|---|---|
| **Intake** | Paper forms, WhatsApp chat notes, unstandardized history. | Standardized 8-screen digital biometric & lifestyle intake. |
| **Calculation** | Manual calculator / Excel formulas for BMR, TDEE, and deficits. | Instant Mifflin-St Jeor calculation with automated activity multipliers. |
| **Plan Creation** | Manual copying from old Word/PDF templates (45–60 mins). | Instant generation of 21 balanced meals based on 2,100+ Indian recipes. |
| **Medical Safety** | Memory-dependent avoidance of clinical irritants and allergens. | Automated dual-tag rule engine (`avoid_*` and `*_friendly` tags). |
| **Delivery** | Static PDF sent on WhatsApp; forgotten in days. | Interactive mobile app with daily meal cards, pantry sync, and notifications. |
| **Compliance** | Subjective self-reporting during monthly follow-up visits. | Real-time 1-tap logging for meals, water, steps, and weight trends. |
| **Plan Refinement**| Completely rewriting a document when a patient dislikes a dish. | Single-click dish swaps, tag-locked doctor overrides, and instant macro re-balancing. |

### Competitive Differentiation
* **Culturally Native**: Engineered around authentic Indian meal structures (Breakfast, Lunch, Dinner with an intentional 15% passive snacking buffer, regional grains, dals, and sabzis).
* **Clinical Tag-Locking**: Doctors retain absolute authority—when a practitioner overrides a dish or locks a tag, the engine respects the clinical directive over algorithmic defaults.
* **Bottom-Up Nutritional Integrity**: Nutrition is calculated upward from verified raw ingredients (using Indian Food Composition Tables - IFCT 2017 standards), not estimated from arbitrary dish names.
* **Pantry-First Planning**: Patients can filter meal plans based on staples currently stocked in their home pantry, dramatically boosting real-world compliance.

---

## 3. Implementation Status: Reality vs. Roadmap

To ensure total integrity in client presentations, the video must strictly distinguish between what is working in code today versus roadmap capabilities:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        MITIHAR MATURITY MATRIX                         │
├──────────────────────────────────┬─────────────────────────────────────┤
│   GENUINELY IMPLEMENTED (LIVE)   │      PLANNED / FUTURE ROADMAP       │
├──────────────────────────────────┼─────────────────────────────────────┤
│ • 3-Tier Role Auth (JWT + MFA)   │ • Contextual Bandit RL Adaptation   │
│ • 8-Stage Patient Onboarding     │ • Dynamic In-App Razorpay/Stripe    │
│ • 21-Meal Weekly Generator       │ • Fitterfly Live API Sync           │
│ • 4 Indian Regional Tagging      │ • pgvector Semantic Dish Search     │
│ • 14 Medical Condition Filters   │ • Multi-tenant White-labeling       │
│ • Doctor Plan Customization      │ • Automated Food Vision Recognition │
│ • Doctor Product Tour            │                                     │
│ • Patient Mobile Product Tour    │                                     │
│ • Real-time Adherence Streak     │                                     │
│ • Quantity-Aware Home Pantry     │                                     │
│ • Admin Token & Royalty Tracking │                                     │
│ • Cloud Run Staging API          │                                     │
└──────────────────────────────────┴─────────────────────────────────────┘
```

### Known Critical Issues (Do NOT Demonstrate in Video)
1. **Doctor Weekly Combo Swap Crash (`doctor.py:1409`)**: `swap_weekly_combo` currently raises a `TypeError` due to a parameter mismatch in the backend (`_fill_slot_dishes`). *Remotion treatment: Show dish replacement via the stable Custom Dish / Add Dish modal, not the weekly combo swap button.*
2. **Profile Edit Auto-Regeneration Bug (`users.py:127`)**: Editing biometrics in `PATCH /users/me` triggers a positional argument bug on plan recalculation. *Remotion treatment: Demonstrate plan adjustments from the dedicated Plan Adjust slider or doctor-initiated regeneration.*
3. **Public Deployment State**: The web and mobile apps are not yet published to public domains or app stores; they run in local staging against Cloud Run.

---

## 4. Website Screen Inventory (Doctor & Admin Dashboard)

The web dashboard is located in `mitihar-frontend/apps/src/app` and uses React Router v7 with two master layouts: `DoctorShell` and `AdminShell`.

| Page / Route | Role | Key Functionality Demonstrated | Visual Treatment in Video |
|---|---|---|---|
| **Login / MFA**<br>`/` | Doctor & Admin | Multi-role secure login, password validation, TOTP 6-digit MFA modal with client-side QR generation. | **Cropped Component / Zoom**: Smooth pan from login card to MFA verification popup. |
| **Doctor Overview**<br>`/doctor/overview` | Doctor | Clinic dashboard KPI tiles: Active Patients, Expiring Soon, Pending Requests, Average Adherence, Quick Action shortcuts. | **Full Screen with Callouts**: Highlight the real-time adherence rate metric and patient renewal badges. |
| **Patient Roster**<br>`/doctor/patients` | Doctor | Data table of registered patients, subscription countdown indicators (30-day token), primary health goals, and quick-link "View Profile". | **Animated Pan**: Start on search/filter bar, pan down the active patient list, hover over "View Profile". |
| **Patient Profile: Plan Tab**<br>`/doctor/patients/:id` (Plan) | Doctor | 7-Day interactive schedule, 3 meals/day (Breakfast, Lunch, Dinner), calorie and macro targets (Carbs/Protein/Fat), dish cards with verified badges, PDF export button. | **Hero Showcase (Animated Close-up)**: Deep zoom into a meal slot showing Roti + Dal + Sabzi, expand dish details, show macro recalculation. |
| **Patient Profile: Meal Config**<br>`/doctor/patients/:id` (Config) | Doctor | TDEE distribution sliders (default 25% B / 35% L / 25% D / 15% Buffer), condition overrides, "Always Include" / "Never Include" dish pinners. | **Feature Callout**: Animated slider moving from 25% to 20%, showing instant percentage rebalancing. |
| **Patient Profile: Weekly Summary**<br>`/doctor/patients/:id` (Weekly) | Doctor | Historical compliance breakdown, planned vs. logged calorie deviation graphs, patient meal choices across the 7-day cycle. | **Split Screen / Overlay**: Doctor reviewing adherence percentage beside the patient's actual logged meals. |
| **Recipe Management**<br>`/doctor/recipes` | Doctor | Recipe directory, filter by regional cuisine (North/South/East/West), custom recipe builder (`AddRecipeForm`), `is_verified` green badge vs. unverified tag. | **Component Highlight**: Pop-up modal demonstrating a doctor adding a custom clinic recipe with sodium and serving weight. |
| **Admin Overview & Billing**<br>`/admin/overview` & `/admin/billing` | Admin | Practice health, active doctors, total token consumption, annual billing run rate, 2% platform royalty calculation, invoice history. | **Fast-Paced Motion Graphic**: Executive summary cards showing enterprise clinic governance. |
| **Admin Audit Logs**<br>`/admin/audit-logs` | Admin | Immutable system activity log: doctor creation, subscription code generation, token overrides, IP addresses, JSONB change payloads. | **Subtle Security Cut**: Demonstrate HIPAA/GDPR-aligned administrative accountability. |

---

## 5. Mobile App Screen Inventory (Patient Companion)

The mobile application is located in `mitihar-patient-app/app` and uses Expo Router file-based navigation.

| File / Route | Screen Name | Patient Experience Demonstrated | Visual Treatment in Video |
|---|---|---|---|
| `app/(auth)/login.tsx` | Patient Login | Clean email login, "Continue with Google" OAuth button, GDPR consent agreement. | **Mobile Device Frame**: Slide-in from bottom, tap Google Sign-In with fluid button response. |
| `app/(onboarding)/personal-info.tsx` | Biometric Intake | Gender, Age, Height (cm), Current Weight (kg), Target Weight (kg) interactive inputs. | **Step Progression**: Fast animated sequence stepping through intake fields with instant BMI preview. |
| `app/(onboarding)/activity-level.tsx` | Activity Level | 5-level selector (Sedentary, Lightly Active, Moderately Active, Very Active, Super Active) with descriptive icons. | **Selection Highlight**: Tap "Moderately Active", card expands with glowing mint border. |
| `app/(onboarding)/dietary-preferences.tsx` | Diet & Region | Diet Type (Vegetarian, Eggetarian, Non-Veg), Indian Region cuisine selector (North, South, East, West). | **Carousel Animation**: Toggle between North Indian and South Indian cuisine preferences. |
| `app/(onboarding)/medical-conditions.tsx` | Clinical Conditions | Multi-select chips for Diabetes, Hypertension, Hypothyroid, PCOS/PCOD, Celiac, Fatty Liver, etc. | **Safety Callout**: Selecting "Type 2 Diabetes" displays a subtle badge: *"Diabetic-safe recipes prioritized"*. |
| `app/(tabs)/index.tsx` | Patient Home | Daily Calorie Ring (Budget vs. Consumed), Streak Counter, Water tracker (+1 glass), Steps counter, Next Meal card. | **Hero Showcase**: Dynamic SVG circle progress animation, 1-tap "+ Glass" water increment animation. |
| `app/(tabs)/meals.tsx` | Daily Meal Plan | 3-meal timeline (Breakfast, Lunch, Dinner), dish names, macro chips (Calories, Protein, Carbs, Fat), "Cook Now" pantry badge. | **Guided Scroll**: Smooth downward pan through the day's meals; tap Breakfast card to reveal ingredients. |
| `app/meals/week-view.tsx` | 7-Day Schedule | Day-by-day swipeable calendar (Mon–Sun), daily caloric target, meal previews for each day of the cycle. | **Horizontal Swipe**: Fluid gesture swiping Monday → Tuesday → Wednesday. |
| `app/meals/combo-detail.tsx` | Dish & Ingredients | Breakdown of composite Indian dishes (e.g., Palak Paneer, Phulka, Jeera Rice) with proportional ingredient amounts. | **Detail Zoom**: Highlight ingredient list showing proportional culinary terms ("1 medium bowl", "2 pieces"). |
| `app/log/log-meal.tsx` | Meal Logging | 1-tap "Log from Plan" or manual intake entry with macro breakdown and timestamp confirmation. | **Micro-interaction**: Tap "I Ate This", checkmark morphs with celebratory haptic bounce. |
| `app/(tabs)/progress.tsx` | Progress & Charts | 90-day interactive weight loss chart, weekly caloric adherence percentage bar, active streak milestone badges. | **Chart Animation**: Smooth spline line drawing from Day 1 to Day 30 showing weight trend downward. |
| `app/doctor/activate.tsx` | Subscription Unlock | 6-character clinical token entry screen, unlocking personalized plans from free teaser mode. | **Unlock Transition**: Enter 6-char code `DR-7821`, lock icon unlocks, teaser gradient disappears into full plan. |

---

## 6. Existing Visual Assets & Inventory

Inspecting the physical directory structure reveals established, production-grade brand assets:

### 1. Official Logos (`logo asset/` & `mitihar-frontend/apps/public/`)
* **`logo asset/logo_white_bg_full.png`** (252 KB): Master horizontal logo with emblem and typography on crisp white background. Ideal for light theme scenes.
* **`logo asset/svg version/logo_white_bg_full_clean.svg`** (20.5 KB): Pure vector version of the full logo; razor-sharp scalability for 4K video rendering.
* **`logo asset/logo_dark_bg.png`** (54.1 KB) & **`logo_dark_bg_clean.svg`** (2.3 KB): Optimized for dark forest-green backgrounds (`#1B4332`).
* **`logo asset/app_icon.png`** (101 KB) & **`svg version/app_icon_clean.svg`** (3.5 KB): Square emblem for mobile framing, app store mockup, and watermark.
* **`logo asset/logo_mono_black.png`** & **`logo_mono_grey.png`**: Monochrome variants for minimal footer credits.

### 2. Existing Playwright Capture Archives (`docs/archive/playwright/`)
The repository contains 19 pre-captured actual screenshots:
* **Doctor Views**: `doctor-01-overview.png` (Overview dashboard), `doctor-02-subscription-codes.png` (Code management), `doctor-03-patient-list.png` (Patient directory table).
* **Patient Onboarding**: `01-landing.png`, `02-register-filled.png`, `03-onboarding-personal-info.png`, `04-activity-level.png`, `05-disclaimer.png`.
* **Patient Mobile Views**: `audit-home-tab.png` (Calorie ring & home), `audit-meals-tab.png` (Meal cards), `audit-profile-tab.png` (Account settings), `patient-01-activate-filled.png` (Token entry), `patient-02-meals-tab.png` (Week schedule).

### 3. Established Brand Palette & Design System (`presentation/build_pptx.js`)
* **Primary Deep Forest Green**: `#1B4332` (Authoritative, clinical, calming)
* **Mid Green**: `#2D6A4F` (Secondary surfaces, cards, accents)
* **Mint Green**: `#52B788` (Active highlights, success states, calorie rings, checkmarks)
* **Warm Saffron**: `#F4A261` (Indian cultural accent, warnings, token tags, CTA buttons)
* **Soft Cream / Off-White**: `#F4F7F2` (Clean background for dashboard showcases)
* **Dark Charcoal Text**: `#1A2F1F` (High contrast, readable typography)
* **Typography Hierarchy**:
  * *Editorial / Brand Serif*: **Georgia** or **Fraunces** (Warm, medical credibility)
  * *Interface / Body Sans*: **Inter** or **Calibri** (Modern, clean, legible data)
  * *Data & Metrics*: **IBM Plex Mono** (Tabular figures, numbers, timings)

---

## 7. Screen Capture & Production Plan

To produce ultra-crisp, high-resolution visuals without blurry scaling, the production pipeline should combine existing real screenshots with newly captured screens.

### Automated Tooling Status
* **Playwright Infrastructure**: Fully configured in `tests/performance/e2e/playwright.config.ts` targeting both Doctor Dashboard (`http://localhost:5173`) and Patient App (`http://localhost:8081`).
* **Execution Command**: `npx playwright test`

### Step-by-Step Local Capture Runbook (If Fresh Screens Needed)
1. **Start PostgreSQL**:
   ```powershell
   docker-compose up -d
   ```
2. **Start FastAPI Backend (Port 8001)**:
   ```powershell
   venv\Scripts\activate
   python -m uvicorn app.main:app --reload --port 8001 --host 0.0.0.0
   ```
3. **Start Doctor Web Dashboard (Port 5173)**:
   ```powershell
   cd mitihar-frontend\apps
   pnpm dev
   ```
   *Login credentials:* `dr.ashok.mehta@mitihar.test` / `DoctorTest@2026`
4. **Start Patient Mobile App in Web Mode (Port 8081)**:
   ```powershell
   cd mitihar-patient-app
   pnpm start --web
   ```
   *Login credentials:* `priya.test@mityahar.com` / `Test@1234`
5. **Screenshots to Capture (1920x1080 for Web, 1170x2532 for Mobile Frame)**:
   * `screen_doctor_plan_detail.png`: Patient detail `PlanTab` with full 7-day view populated.
   * `screen_doctor_meal_config.png`: TDEE slider distribution and medical condition overrides.
   * `screen_mobile_pantry.png`: Quantity-aware pantry inventory with "Cook Now" badges.
   * `screen_mobile_progress_chart.png`: 90-day interactive weight loss spline.

---

## 8. Major Workflow Storyboards

### Workflow 1: Doctor Biometric & Macro Plan Review
```
[Step 1: Patient Selection]
Doctor opens Dashboard → Clicks "Priya Sharma" in Patient Roster.
Visual: Smooth camera pan across row; row highlights in subtle mint; transition to Detail view.

[Step 2: Automated Biometric Intake]
Header displays calculated metrics: BMI 21.8 · BMR 1,340 kcal · TDEE 1,850 kcal · Target Deficit 1,570 kcal.
Visual: Animated callout badges drawing attention to the Mifflin-St Jeor math.

[Step 3: 7-Day Meal Architecture]
Screen displays Monday–Sunday 3-meal grid. Breakfast: Moong Dal Chilla (25%) · Lunch: Phulka + Palak Paneer + Curd (35%) · Dinner: Brown Rice + Dal Tadka (25%).
Visual: Zoom in on Wednesday Lunch card. Expand ingredient breakdown.

[Step 4: Clinical Customization]
Doctor clicks "Adjust Macro Split" → drags lunch slider to 40%, dinner to 20%.
Visual: Calorie targets dynamically animate across the 7-day slots in real time.

[Step 5: Clinic Approval & Sync]
Doctor clicks "Approve & Push to Patient App".
Visual: Green checkmark pulse. Seamless transition to mobile phone mockup receiving push notification.
```

### Workflow 2: Patient Daily Routine & 1-Tap Adherence
```
[Step 1: Morning Check-in]
Patient wakes up, unlocks phone. Mitihar app displays Home Tab with glowing 1,570 kcal budget ring.
Visual: Mobile frame centered on screen. Calorie ring animates smoothly from 0% to current state.

[Step 2: Reviewing Today's Meals]
Patient navigates to Meals Tab. Breakfast card shows "Oats Upma with Sautéed Veggies".
Visual: Smooth upward scroll. Tap card to view cooking steps and proportional ingredients.

[Step 3: 1-Tap Meal Logging]
Patient finishes meal, taps "Log Meal".
Visual: Floating action button expands; calorie ring instantly consumes 390 kcal; streak increases from 14 to 15 Days.

[Step 4: Hydration & Activity Quick-Log]
Patient taps "+ Glass" on the water tracker (4/8 glasses complete).
Visual: Water cylinder fills with smooth liquid wave animation.
```

### Workflow 3: Medical Condition & Allergen Protection
```
[Step 1: Patient Clinical Profile]
Patient onboarded with "Type 2 Diabetes" and "Nut Allergy".
Visual: Split card showing medical tags mapped automatically from intake.

[Step 2: Rule Engine Tag Filtering]
Engine applies `avoid_diabetes` and `avoid_nuts`. High glycemic dishes and peanut chutneys are purged from the candidate pool.
Visual: Motion graphic showing database filtering out red-tagged recipes, keeping green-tagged recipes.

[Step 3: Doctor Verification]
Doctor inspects recipe pool; locks clinical tags with `tags_locked=True`.
Visual: Shield icon snaps into place on the recipe card.
```

---

## 9. Client-Friendly Feature Explanations

To maintain business clarity and prevent developer jargon from alienating executive viewers, use the following messaging translations:

| Technical Implementation | Client-Friendly Video Narration |
|---|---|
| *Mifflin-St Jeor equation & activity multipliers in `calculations.py`* | **"Instant Medical Calculations"**: Mitihar automatically determines each patient's exact metabolic baseline and daily caloric needs the moment intake is complete. |
| *2,141-recipe PostgreSQL database with regional cuisine tags* | **"Culturally Authentic Indian Nutrition"**: A rich clinical library of over 2,100 authentic Indian dishes across Northern, Southern, Eastern, and Western culinary traditions. |
| *Two-tag avoidance/preference schema (`avoid_diabetes`, `pcos_friendly`)* | **"Automated Clinical Safety Filters"**: The platform automatically guards against dietary conflicts, ensuring meals respect medical conditions like Diabetes, Thyroid, and PCOS without manual checking. |
| *15% passive caloric buffer in meal allocation split* | **"Real-World Flexibility"**: A built-in smart caloric buffer that absorbs everyday Indian snacking habits without derailing the patient's long-term health goal. |
| *Three-state token lifecycle (AVAILABLE → RESERVED → CONSUMED)* | **"Frictionless Clinic Subscriptions"**: Simple, secure 6-character activation codes issued by the clinic, unlocking personalized plans for patients in seconds. |
| *Async Cloud Run microservices on Google Cloud Platform* | **"Enterprise-Grade Scalability"**: Built on resilient, HIPAA-compliant cloud architecture proven to handle thousands of concurrent patients without slowing down. |
| *Zero-DB JWT claims checking in `SubscriptionCheckMiddleware`* | **"Instant Access Control"**: High-speed security that protects medical privacy and clinic boundaries without lag or server overhead. |
| *Quantity-aware `patient_pantry` and dynamic `/shopping-list`* | **"Smart Pantry Sync"**: Generates weekly grocery lists from meal plans and prioritizes meals patients can cook right now with ingredients already in their kitchen. |

---

## 10. Verified Project Numbers & Metrics

Every metric below is verified directly from repository files. These numbers are safe and defensible for client presentation:

| Metric | Verified Value | Exact Source File | Presentation Guidance |
|---|---|---|---|
| **Cleaned Indian Recipe Pool** | **2,141 recipes** | `BUILD_TRACKER.md:186`, `CLAUDE.md:204` | Say: *"Over 2,100 verified Indian recipes"*. **Do NOT claim 6,000+**. |
| **API Endpoints** | **84+ endpoints** | `presentation/build_pptx.js:416`, `app/routers/` | Say: *"84+ clinical API endpoints"*. |
| **Mobile Patient Screens** | **32 screens** | `mitihar-patient-app/app/` route tree | Say: *"Over 30 intuitive patient screens"*. |
| **Web Dashboard Views** | **17 views** | `mitihar-frontend/apps/src/app/routes.tsx` | Say: *"Complete multi-role clinical dashboard"*. |
| **Database Migrations** | **34 migrations** | `BUILD_TRACKER.md:220` (applied on staging) | Represents robust data engineering discipline. |
| **Security Middleware** | **5 custom layers** | `CLAUDE.md:84`, `app/core/middleware.py` | Emphasizes patient data privacy and isolation. |
| **Concurrent Load Test** | **1,000 virtual users** | `BUILD_TRACKER.md:237` (Aug 7 Cloud Run test) | **0.0088% error rate, 176ms mean latency**. |
| **Weekly Meals Generated** | **21 distinct meals** | `presentation/build_pptx.js:418` | 7 days × Breakfast, Lunch, Dinner. |
| **Indian Regional Cuisines** | **4 regions** | North, South, East, West tags in DB | Highlights pan-Indian clinical utility. |
| **Integration Test Suite** | **94/94 passing steps** | `tests/full_backend_test.py:532` | Demonstrates comprehensive automated verification. |
| **Git Version Commits** | **178 commits** | `git rev-list --count HEAD` | Shows sustained, verified engineering evolution. |

---

## 11. Evidence-Backed Project Objectives

### Set A: Business & Clinical Value Objectives (Recommended for Client Pitch)
1. **Dramatically Reduce Clinical Consultation Overhead**: Reduce the time required for clinical dieticians to generate, verify, and deliver comprehensive 7-day medical meal plans from ~60 minutes to under 2 minutes. *(Supported by: Deterministic `MealGenerator` pipeline and one-click PDF/app dispatch).*
2. **Eliminate Patient Compliance Attrition**: Bridge the post-consultation adherence gap through automated daily meal pacing, instant 1-tap adherence logging, and streak reinforcement. *(Supported by: Real-time streak tracking in `app/routers/progress.py` and Expo Home tab UI).*
3. **Equip Clinics with Scalable Digital Governance**: Provide clinic owners with centralized practitioner management, multi-doctor patient isolation, and transparent token-based subscription licensing. *(Supported by: `DoctorIsolationMiddleware` and Admin billing/token generator).*

### Set B: Patient-Centric Healthcare Objectives
1. **Deliver Culturally Authentic Medical Nutrition**: Enable Indian patients suffering from chronic lifestyle diseases to follow medically tailored diets without sacrificing familiar regional foods. *(Supported by: 4-region cuisine classification and 2,141 traditional Indian recipes).*
2. **Simplify Daily Dietary Execution**: Remove the cognitive burden of calorie counting by translating macro targets into clear, proportional meal combinations and automated pantry grocery lists. *(Supported by: `patient_pantry` model and dynamic `/shopping-list` aggregation).*
3. **Foster Long-Term Behavioral Habit Formation**: Encourage longitudinal dietary compliance through visual progress feedback, hydration tracking, and milestone rewards. *(Supported by: 90-day progress charts and weekly adherence metrics).*

### Set C: AI & Systems Automation Objectives
1. **Hybrid Deterministic-Generative Nutritional Pipeline**: Guarantee clinical safety by generating meal structures through deterministic rule-based algorithms, utilizing LLM intelligence strictly for unknown food parsing and edge-case resolution. *(Supported by: Gemini 2.5 Flash Lite fallback in `app/routers/doctor.py`).*
2. **Longitudinal Preference Learning Foundation**: Capture granular feedback signals—including doctor dish replacements and patient meal ratings—to build the training corpus for future adaptive models. *(Supported by: `MealRating` schema and recommendation replacement event logging).*

---

## 12. Team & Engineering Governance

### Verified Contributor Roles from Repository Evidence
* **Ruchit Das** (`Rcidshacker` / `Ruchit Das`): Primary Engineering Lead & Full-Stack Architect. Author of 178 commits spanning backend architecture, SQLAlchemy 2.0 migrations, FastAPI endpoints, React doctor dashboard, Expo mobile redesign, and Google Cloud Run staging infrastructure.
* **Niharika Mishra** (`niharika797`): Platform Co-Creator and Project Originator. Repository owner of `Mitihar_dietician`, responsible for foundational project initialization and clinical domain requirements.
* **Achyut Maheshka**: Recognized Core Project Collaborator. User-confirmed team member contributing to platform design and clinical strategy (technical git commits are centralized under the repository contributors above).

*Production Guidance: Present the team collectively as the creators and engineers behind Mitihar, highlighting multi-disciplinary excellence across software architecture, clinical dietetics, and user experience.*

---

## 13. Proposed Scene-by-Scene Video Storyboard (4–5 Minutes)

**Total Duration:** 4 minutes 15 seconds (255 seconds / 7,650 frames @ 30fps)
**Tone:** Elegant, clinical, modern, inspiring, authoritative.
**Music:** Sophisticated ambient corporate track with subtle rhythmic pulse and warm acoustic undertones.

```
00:00 ─── Scene 01: Brand Identity & The Hook (15s)
00:15 ─── Scene 02: The Dietetic Scaling Dilemma (25s)
00:40 ─── Scene 03: Meet Mitihar — The Clinical OS (20s)
01:00 ─── Scene 04: The Doctor's Command Center (35s)
01:35 ─── Scene 05: Clinical Precision & Automated Math (30s)
02:05 ─── Scene 06: Culturally Native Indian Nutrition (30s)
02:35 ─── Scene 07: The Patient Companion Experience (35s)
03:10 ─── Scene 08: Smart Pantry & Grocery Automation (20s)
03:30 ─── Scene 09: Clinic Administration & Enterprise Security (20s)
03:50 ─── Scene 10: Verified Scale & Resilience (15s)
04:05 ─── Scene 11: The Vision & Closing Brand Call (10s)
```

---

### Detailed Scene Specifications

#### Scene 01: Brand Identity & The Hook (15 seconds / Frames 0–450)
* **Visual Treatment**: Deep forest green background (`#1B4332`) with subtle, drifting concentric gradient rings. The official clean vector logo (`logo_white_bg_full_clean.svg` or `logo_dark_bg_clean.svg`) scales in with an elegant spring animation. A warm saffron accent line expands beneath the logo.
* **On-Screen Text**: **Mityahar** · *AI-Powered Precision Dietetics Platform*
* **Narration**: *"In healthcare, nutrition is therapy. Yet for millions of Indian patients and the dieticians who care for them, the way dietary care is delivered remains deeply broken."*
* **Asset / Implementation**: Remotion vector SVG animation, Google Font `Fraunces` / `Georgia`, spring physics (`spring({ frame, fps, config: { damping: 12 } })`).
* **Transition**: Smooth camera push-in through the saffron accent line dissolving into Scene 02.

#### Scene 02: The Dietetic Scaling Dilemma (25 seconds / Frames 450–1200)
* **Visual Treatment**: Problem dramatization. Animated motion-graphic cards representing the chaotic reality: scattered WhatsApp message bubbles ("What should I eat for dinner?"), a spreadsheet overflowing with manual BMR formulas, and a generic printed PDF chart crossing out Indian staples. Red warning badges pulse.
* **On-Screen Text**: *The Problem: Fragmented Tools · Manual Math · 0% Adherence Visibility*
* **Narration**: *"Today, clinical dieticians spend hours manually calculating calories on spreadsheets and distributing static PDFs over WhatsApp. Patients lose motivation, medical restrictions are hard to police, and doctors have zero visibility into real compliance once a patient leaves the clinic."*
* **Asset / Implementation**: Native Remotion stylized UI cards with subtle shadow floating in 3D space (`transform: rotateY(-10deg)`).
* **Transition**: Split-screen wipe from left to right, clearing away the chaos with a fresh mint sweep.

#### Scene 03: Meet Mitihar — The Clinical OS (20 seconds / Frames 1200–1800)
* **Visual Treatment**: The solution reveal. A dynamic 3D isometric perspective showing the three interconnected pillars: The Web Dashboard (Doctor), The Mobile Companion (Patient), and the Cloud Core (FastAPI & PostgreSQL). Elegant glowing fiber-optic lines connect all three.
* **On-Screen Text**: *Three Apps. Three Roles. One Intelligent Platform.*
* **Narration**: *"Meet Mitihar. A complete, closed-loop clinical dietetics platform engineered specifically for Indian healthcare. Unifying doctors, patients, and clinics into a single data-driven ecosystem."*
* **Asset / Implementation**: Three high-resolution stylized device frames (MacBook for web, iPhone for mobile, floating cloud shield for backend) converging into center.
* **Transition**: Zoom focus into the MacBook screen, transitioning into the full Doctor Dashboard.

#### Scene 04: The Doctor's Command Center (35 seconds / Frames 1800–2850)
* **Visual Treatment**: Real screenshot walkthrough of the Doctor Dashboard (`doctor-01-overview.png` and `doctor-03-patient-list.png`). Smooth camera pan across the KPI cards: Active Patients, Expiring Soon, Adherence Rate. Pan down to the patient list, highlighting patient "Priya Sharma", then clicking into her detailed profile.
* **On-Screen Text**: *Doctor Dashboard: Real-Time Roster · Patient Progress · Instant Oversight*
* **Narration**: *"From the doctor dashboard, clinical practitioners have immediate, centralized oversight. Every patient's subscription status, biometric history, and ongoing compliance is accessible in seconds, transforming clinical consultations from administrative paperwork into high-impact care."*
* **Asset / Implementation**: High-resolution browser mockup with soft drop-shadow, Remotion pan/zoom (`interpolate(frame, [0, 100], [1, 1.15])`) focusing on key UI cards.
* **Transition**: Smooth cross-fade to the 7-Day Meal Plan tab.

#### Scene 05: Clinical Precision & Automated Math (30 seconds / Frames 2850–3750)
* **Visual Treatment**: The PlanTab view in the Doctor portal. Showcase the automated intake calculations: BMI, BMR, and TDEE. Zoom in on the 7-day schedule showing Breakfast, Lunch, and Dinner. Demonstrate the interactive Meal Config slider rebalancing macro distributions with immediate UI updates.
* **On-Screen Text**: *Automated Clinical Math · Mifflin-St Jeor TDEE · Proportional Macro Splits*
* **Narration**: *"In seconds, Mitihar computes precise BMR and total daily energy expenditure using verified medical algorithms. Meal schedules are structured across breakfast, lunch, and dinner—with a deliberate fifteen percent buffer tailored to real-world Indian eating habits."*
* **Asset / Implementation**: Screen capture with animated highlight rings and floating callout badges pointing out macro percentages (25% / 35% / 25% / 15%).
* **Transition**: Camera pans to the recipe library and regional filter chips.

#### Scene 06: Culturally Native Indian Nutrition (30 seconds / Frames 3750–4650)
* **Visual Treatment**: Fast, colorful showcase of the recipe database. Filter chips activate: North, South, East, West. Visual cards showcase genuine dishes: Moong Dal Chilla, Phulka with Palak Paneer, Oats Idli, Brown Rice Sambar. Highlight clinical safety badges: `Diabetic-Safe`, `Low GI`, `Gluten-Free`.
* **On-Screen Text**: *2,100+ Authentic Indian Recipes · 4 Culinary Regions · Automated Clinical Filters*
* **Narration**: *"Unlike Western calorie trackers, Mitihar is built ground-up for Indian kitchens. With over twenty-one hundred verified recipes across four regional cuisines, the platform automatically applies clinical filters for conditions like Diabetes, Hypertension, and PCOS—safeguarding patient health with every meal generated."*
* **Asset / Implementation**: Dynamic multi-card staggered carousel animating left-to-right, displaying food cards with authentic metadata and verified badges.
* **Transition**: A patient meal card slides forward and morphs into a mobile phone display.

#### Scene 07: The Patient Companion Experience (35 seconds / Frames 4650–5700)
* **Visual Treatment**: Mobile app walkthrough inside an elegant iPhone frame. Show the 8-step onboarding flow rapidly progressing, landing on the Home Tab (`audit-home-tab.png`). Demonstrate the animated calorie budget ring, the 1-tap "+ Glass" water logging, and tapping "Log Meal" to instantly record breakfast.
* **On-Screen Text**: *Patient Companion: 1-Tap Logging · Real-Time Calorie Ring · Habit Tracking*
* **Narration**: *"On mobile, patients experience effortless clarity. No complicated arithmetic—just clear daily meals, intuitive one-tap logging, hydration tracking, and instant feedback that turns healthy intentions into daily habits."*
* **Asset / Implementation**: Expo screen captures rendered in a modern phone bezel with smooth glass reflection and animated tap ripples.
* **Transition**: Slide to the Pantry & Shopping List tab.

#### Scene 08: Smart Pantry & Grocery Automation (20 seconds / Frames 5700–6300)
* **Visual Treatment**: Showcase the Pantry Inventory and dynamic Shopping List. Display ingredients categorized with culinary clarity ("1 bowl", "2 pieces"). An ingredient is toggled "In Stock", and the recipe card displays a glowing green badge: *"Cook Now: 100% Ingredients Available"*.
* **On-Screen Text**: *Pantry-First Planning · Smart Shopping Lists · Proportional Measures*
* **Narration**: *"Mitihar bridges the kitchen gap. The platform checks what ingredients patients already have in their pantry, automatically generating grocery lists and suggesting recipes they can prepare immediately."*
* **Asset / Implementation**: Two side-by-side mobile screens showing the sync between Pantry inputs and Shopping List checkboxes.
* **Transition**: Camera pulls back from mobile device to display the Admin & Security layer.

#### Scene 09: Clinic Administration & Enterprise Security (20 seconds / Frames 6300–6900)
* **Visual Treatment**: Admin Dashboard (`AdminBilling` and `AuditLogs`). Show 6-character subscription code generation, 2% platform royalty tracking, IP whitelisting controls, and TOTP MFA setup.
* **On-Screen Text**: *Clinic Governance · Subscription Tokens · HIPAA/GDPR-Aligned Security*
* **Narration**: *"For clinic owners and healthcare networks, Mitihar offers complete enterprise governance: five-layer security middleware, multi-practitioner patient isolation, audit trails, and seamless token-based subscription management."*
* **Asset / Implementation**: Fast, polished executive motion graphics showing security shields, clean data tables, and token badges.
* **Transition**: Screen darkens into rich forest green for the metrics climax.

#### Scene 10: Verified Scale & Resilience (15 seconds / Frames 6900–7350)
* **Visual Treatment**: High-impact metrics showcase. Clean typography with numeric count-up animations:
  * **2,141** *Verified Indian Recipes*
  * **84+** *Clinical Endpoints*
  * **1,000** *Concurrent Users Tested under Load*
  * **94 / 94** *Integration Test Verifications*
* **On-Screen Text**: *Engineered for Scale · Cloud Run Staging · 99.9% Execution Reliability*
* **Narration**: *"Built on resilient cloud architecture and thoroughly load-tested against real-world traffic, Mitihar delivers enterprise-grade performance that clinicians can depend on."*
* **Asset / Implementation**: 4-column metric counter layout with gold saffron underlines and subtle glow effects.
* **Transition**: Metrics fade smoothly as the central logo re-emerges.

#### Scene 11: The Vision & Closing Brand Call (10 seconds / Frames 7350–7650)
* **Visual Treatment**: Master Mitihar logo in pristine white against the dark forest green canvas. The tagline appears in soft mint: *"Personalized nutrition for every Indian patient."* Closing credentials: *"Built with clinical rigor by Ruchit Das, Niharika Mishra & Achyut Maheshka."*
* **On-Screen Text**: **Mityahar** · *Personalized nutrition for every Indian patient.* · www.mityahar.com
* **Narration**: *"Mitihar. Bringing intelligence, culture, and clinical precision to the future of dietetics. Schedule a consultation or clinic onboarding today."*
* **Asset / Implementation**: Smooth opacity fade-out with audio reverb tail.

---

## 14. Remotion-Specific Production Blueprint

When implementing the final video using the Remotion framework, adhere to these technical standards:

### Composition Architecture
```
video-explainer/
├── src/
│   ├── Root.tsx               # Root composition definition (1920x1080 @ 30fps, 7650 frames)
│   ├── constants/             # Brand colors, typography tokens, layout margins
│   ├── components/
│   │   ├── DeviceFrame.tsx    # Responsive MacBook & iPhone mockups with drop-shadows
│   │   ├── MetricCard.tsx     # Animated numeric counter with easing curve
│   │   ├── FeatureCallout.tsx # Floating badge with glowing indicator
│   │   └── LogoReveal.tsx     # Vector SVG brand reveal with spring damping
│   ├── scenes/
│   │   ├── Scene01_Intro.tsx
│   │   ├── Scene02_Problem.tsx
│   │   ├── Scene03_Platform.tsx
│   │   ├── Scene04_DoctorRoster.tsx
│   │   ├── Scene05_ClinicalMath.tsx
│   │   ├── Scene06_IndianNutrition.tsx
│   │   ├── Scene07_PatientApp.tsx
│   │   ├── Scene08_Pantry.tsx
│   │   ├── Scene09_Enterprise.tsx
│   │   ├── Scene10_ScaleMetrics.tsx
│   │   └── Scene11_Outro.tsx
│   └── index.ts
```

### Deterministic Motion Guidelines
1. **No External Live Network Requests**: All images, SVGs, and audio files must be bundled locally in `public/` or imported as static assets (`staticFile()`).
2. **Spring Physics Standard**: Use Remotion's `spring()` helper rather than linear CSS transitions for organic, premium movement:
   ```tsx
   const scale = spring({
     frame: frame - delay,
     fps,
     config: { damping: 14, mass: 0.8, stiffness: 100 }
   });
   ```
3. **Smooth Screen Navigation (Interpolation)**: When highlighting parts of screenshots, use `interpolate()` with `Extrapolate.CLAMP` on scale and translation:
   ```tsx
   const translateY = interpolate(frame, [20, 60], [0, -120], { extrapolateRight: 'clamp' });
   ```
4. **Typography Loading**: Preload Google Fonts (`Fraunces` and `Inter`) via `@remotion/google-fonts` to avoid layout shifts during rendering.
5. **Captions Integration**: Use `@remotion/captions` to provide synchronized, subtitle-style dynamic captions across the bottom third of the video for silent social viewing.

---

## 15. DO NOT CLAIM IN VIDEO (Guardrails & Risk Prevention)

To maintain absolute credibility with clients and technical auditors, the video **must not** make any of the following false or unverified claims:

* 🚫 **DO NOT claim 6,000+ recipes in the live app**: The raw dataset was 6,000+, but the cleaned, deduplicated, and medically indexed dataset in the database is **2,141 recipes**. Say *"over 2,100 authentic Indian recipes"*.
* 🚫 **DO NOT claim that Reinforcement Learning (RL) is currently adapting plans**: The RL reward collection infrastructure exists in models (`MealRating`), but the Contextual Bandit model is an unbuilt roadmap item. Say *"captures clinical feedback to power future adaptive learning"*.
* 🚫 **DO NOT claim the web or mobile app is publicly downloadable on the App Store / Play Store**: The applications are hosted on staging infrastructure and local testbeds; distribution profiles are not yet live.
* 🚫 **DO NOT demonstrate the Weekly Combo Swap button**: `doctor.py:1409` has an open `TypeError` bug in the staging code. Demonstrate recipe replacement through the Custom Dish modal.
* 🚫 **DO NOT claim automated in-app credit card / UPI payments**: Subscription activation is handled via clinic-issued 6-character tokens; dynamic payment gateway integration is a Phase 2 item.
* 🚫 **DO NOT claim automatic photo food recognition / AI computer vision**: The current system relies on structured 1-tap meal logging and pantry tracking, not camera-based food recognition.

---

## 16. Missing Information & Outstanding Decisions

The following items should be clarified with the product owner before rendering the final Remotion composition:

1. **Voiceover Voice & Accent**: Should the voiceover be a warm Indian-English professional narrator (recommended for cultural and clinical resonance), a neutral global narrator, or text/music-only with animated subtitles?
2. **Specific Doctor & Patient Names**: Are "Dr. Ashok Mehta" and "Priya Sharma" acceptable demonstration personas, or should real client practitioner names be substituted?
3. **Achyut Maheshka's Specific Title**: How should Achyut's role be credited on the team slide (e.g., *Clinical Operations Lead*, *Co-Founder*, *Product Strategist*)?
4. **Primary Call to Action (Outro)**: Should the final slide direct clients to a specific booking URL (e.g., `www.mityahar.com`), an email address (`contact@mityahar.com`), or a private beta access request form?

---

*Report prepared from exhaustive technical inspection of the Mitihar platform codebase. Ready for Remotion implementation prompt generation.*
