## The Patient — Who They Are and What They Control

---

### Who is the Patient?

The patient is the **end user** — the person the entire app was built for. Everything the admin controls, everything the doctor manages, every line of code written — it all exists to serve this one person's daily diet journey.

There are two types of patients as we established:

```
Tier 1 — Standalone Patient
Downloaded app independently
No doctor connection
Uses basic AI recommendations
Pays nothing (free) or ₹149/month (premium - Phase 2)

Tier 2 — Doctor Connected Patient
Referred or connected to a doctor
Doctor approved and activated them
Full supervised experience
Doctor pays ₹250/month on their behalf
```

Most features are shared between both tiers. Where they differ it will be clearly marked.

---

### The Patient's Powers — Every Single One

---

#### 1. Registration and Onboarding Request
This is where the patient's journey begins — before they even see the app properly.

**What patient does:**

**Tier 1 — Standalone:**
- Downloads app from Play Store or App Store
- Creates account directly with Google OAuth (no password needed)
- Gets immediate access to basic features
- No waiting. No approval needed.

**Tier 2 — Doctor Connected:**
- Downloads app
- Fills initial request form:
  - Full name
  - Phone number
  - Email (Google account)
  - Age
  - Selects their doctor from a list OR enters a doctor code shared by their doctor
- Submits request
- Sees a waiting screen:
  ```
  "Your request has been sent to Dr. Ashok.
   You will be notified once approved.
   This usually takes 24 hours."
  ```
- Cannot proceed further until doctor approves
- Once approved → enters full onboarding health questionnaire
- Once questionnaire complete → first meal plan generated automatically

**Why this matters:** The waiting gate exists for security and clinical responsibility. Doctor knows every patient they take on. Patient understands they are entering a medically supervised system — not just another calorie counting app.

---

#### 2. Health Profile Setup — The Onboarding Questionnaire
After approval (Tier 2) or immediately (Tier 1), patient fills their full health intake.

**What patient fills — all 7 sections:**

**Section 1 — Body Metrics:**
- Height
- Current weight
- Target weight
- Gender
- Date of birth (age auto-calculated)

**Section 2 — Health Goals:**
- Primary goal (lose weight, gain weight, manage condition, build strength etc.)
- How fast they want to achieve it (slow and steady, moderate, fast)

**Section 3 — Medical Conditions:**
- Diabetes Type 1 or 2
- Hypertension / Low BP
- High cholesterol
- Thyroid (hypo/hyper)
- PCOD / PCOS
- Heart disease
- Kidney disease
- Liver disease
- IBS / Gastric issues
- Anaemia
- Osteoporosis
- Pregnancy / Breastfeeding
- None of the above
- Currently on medication (yes/no, what for)

**Section 4 — Food Allergies (Mandatory — cannot skip):**
- Dairy / Lactose
- Gluten
- Nuts
- Shellfish / Seafood
- Eggs
- Soy
- Nightshades
- None
- Free text for anything else

**Section 5 — Dietary Preferences:**
- Diet type (vegetarian, vegan, eggetarian, non-veg, jain, no onion no garlic)
- Regional food preference (North Indian, South Indian, Bengali etc.)
- Meals per day (2, 3, 3 + snacks, 5-6 small meals)
- Fasting days (yes/no, which days)

**Section 6 — Lifestyle:**
- Activity level (sedentary to extremely active)
- Occupation type
- Sleep hours
- Current water intake
- Smoking / alcohol habits

**Section 7 — Current Eating Habits:**
- Current breakfast pattern
- How often they eat outside
- Fixed meal timing (yes/no)
- Foods they eat daily and value

**After completion:**
- BMI calculated and shown
- BMR calculated and shown
- TDEE calculated and shown
- First 7-day meal plan generated immediately

**Why this matters:** Every answer becomes a filter. Nut allergy = zero nut recipes ever appear. Diabetic = only diabetic-friendly recipes. Jain = no root vegetables. The AI recommendation becomes clinically relevant from day one — not generic.

---

#### 3. Viewing the Weekly Meal Plan
The core daily feature of the app. This is what the patient opens the app for every morning.

**What patient sees:**

```
This Week — March 1 to March 7

Monday
  Breakfast → Poha with vegetables
              Calories: 320  Protein: 8g  
              Carbs: 52g     Fiber: 4g
              Fat: 6g
              [ View Full Recipe ]

  Lunch     → Dal Tadka + 2 Rotis + Cucumber Raita
              Calories: 520  Protein: 22g
              ...

  Dinner    → Palak Paneer + 1 Roti
              Calories: 410  Protein: 18g
              ...

Tuesday
  ...
```

**What patient can do with the meal plan:**
- View each day's full meal plan
- Tap any meal to see full recipe details
- See complete ingredient list per meal
- See step-by-step cooking instructions
- See nutrition breakdown per meal and daily total
- See weekly nutrition summary (total calories, protein etc.)
- Navigate between current week and past weeks
- See doctor's notes attached to specific meals (Tier 2 only)

**Tier 1 vs Tier 2 difference:**
```
Tier 1 → AI generated, no doctor refinement
Tier 2 → AI generated + doctor reviewed and approved
         Doctor may have swapped meals, added notes,
         adjusted portions specifically for this patient
```

**Why this matters:** Patient opens the app every morning and knows exactly what to eat. No decision fatigue. No guessing. Just follow the plan.

---

#### 4. Meal Logging — What You Actually Ate
This is where the patient reports reality back to the system.

**What patient can do:**
- Log each meal as eaten — tap "I had this" on the recommended meal
- If they ate something different — tap "I had something else":
  - Search food database for what they actually ate
  - Or type a custom food name if not in database
- Log the time they ate
- Log portion size (full portion, half portion, double portion)
- Add a quick note (e.g. "felt nauseous after this, skipped lunch")
- Log a meal they ate that was not in today's plan at all
- Edit a logged meal within 24 hours if they made a mistake
- View today's logged meals summary

**What happens after logging:**
```
Patient logs actual meals
        ↓
System compares recommended vs actual
        ↓
Nutrition gap calculated
(e.g. patient ate 300 fewer calories than recommended)
        ↓
Next day's / next week's plan 
adjusts subtly to compensate
        ↓
Doctor can see the comparison 
in their dashboard (Tier 2)
```

**Why this matters:** A diet plan that doesn't know whether you followed it is useless. The logging loop is what makes Mityahar a living, adapting system rather than a static meal chart.

---

#### 5. Progress Tracking
Patient tracks all health metrics in one place.

**What patient can log:**
- Daily water intake (glasses or litres)
- Daily steps count
- Current weight (whenever they weigh themselves)

**What patient can view:**
- Water intake chart — daily over the past 30 days
- Steps chart — daily over the past 30 days
- Weight history graph — their weight journey since joining
- BMI trend — how their BMI has changed over time
- Weekly adherence score — what percentage of meals they followed
- Streak counter — how many consecutive days they logged something
- Milestone celebrations (lost first 2kg, completed first full week etc.)

**Why this matters:** Patients need to see their own progress to stay motivated. Seeing a weight graph going down, even slowly, is more powerful than any prescription.

---

#### 6. Nutrition Insights
Patient understands what they're eating, not just what they're supposed to eat.

**What patient can see:**
- Today's nutrition summary (calories consumed vs target)
- Macronutrient breakdown — protein, carbs, fat, fiber today
- Weekly average nutrition vs recommended target
- Which nutrients they're consistently low on (e.g. "You've been under your protein target 5 of the last 7 days")
- Meal-by-meal calorie contribution (which meal is heaviest)

**Tier 1 vs Tier 2:**
```
Tier 1 → Basic daily calorie and macro view
Tier 2 → Full insights + doctor can add 
         personalised nutrient targets
```

**Why this matters:** Awareness drives behavior. When a patient sees they've had 120% of their carb target by lunchtime — they make a different choice at dinner.

---

#### 7. Weekly Ingredient Checklist / Shopping List
Practical tool that bridges the app and real life.

**What patient can do:**
- View a consolidated ingredient list for the entire week's meal plan
- Ingredients automatically aggregated across all 21 meals (3 meals × 7 days)
- Quantities specified per ingredient
- Mark items as already available at home
- Remaining items form the shopping list
- Share shopping list (WhatsApp, copy text)
- View ingredients organised by category (vegetables, dairy, grains, spices etc.)

**Why this matters:** The biggest reason people don't follow meal plans is they don't have the ingredients. This feature removes that excuse entirely. Patient does one weekly shop and has everything they need.

---

#### 8. Find a Doctor — Tier 1 Only
For standalone users who want to upgrade to supervised care.

**What patient can do:**
- Tap "Find a Doctor Near Me"
- Grant location permission
- See list of registered Mityahar doctors sorted by distance
- Each doctor card shows:
  - Name and photo
  - Specialisation
  - Clinic address
  - Distance from patient
  - Languages spoken
  - Availability status
- Tap any doctor to see their full profile
- Send a connection request to a doctor
- Wait for doctor approval
- Once approved → code consumed → upgrades to Tier 2

**Why this matters:** This is the feature that converts free users into paying patients — driving revenue for both the doctor and for you.

---

#### 9. Notifications and Reminders
App keeps patient on track even when they forget.

**Notifications patient receives:**
- Meal reminders (breakfast, lunch, dinner at set times)
- Water intake reminder (every 2 hours if not logged)
- Weekly meal plan ready notification (every Sunday/Monday)
- Doctor approved your request (Tier 2)
- Doctor updated your meal plan (Tier 2)
- Doctor added a note to your plan (Tier 2)
- Subscription expiry reminder (Tier 2) — "Your plan expires in 3 days, contact your doctor"
- Milestone achieved (lost 1kg, 7-day streak, completed first week)
- Inactivity reminder if no log in 2 days

**What patient can control:**
- Turn individual notification types on or off
- Set preferred meal reminder times
- Set quiet hours (no notifications between X and Y)

**Why this matters:** Consistency is everything in diet. Gentle reminders at the right time are the difference between a patient who follows the plan and one who forgets about the app after week 2.

---

#### 10. Profile Management
Patient manages their own account.

**What patient can do:**
- View and edit personal details (name, phone, profile photo)
- Update physical stats when they change (weight update, for accurate BMR recalculation)
- Update health goals if they evolve
- Update dietary preferences if they change
- Update allergy information
- View their own BMI, BMR, TDEE (recalculated when stats update)
- Change notification preferences
- View subscription status and expiry date (Tier 2)
- Request account deletion (DPDP Act — right to erasure)

**What patient CANNOT edit:**
- Medical conditions once set — requires doctor review before changing (Tier 2)
- Allergy information without a confirmation step — accidental removal of an allergy could be dangerous

**Why this matters:** Patient's body changes. Goals evolve. A patient who lost 10kg now has a different target weight. The profile must reflect reality for the AI to keep recommendations relevant.

---

#### 11. Recipe Detail View
Patient can explore any meal recommended to them in full detail.

**What patient sees on a recipe page:**
- Recipe name (and original name if regional)
- Food photo
- Cuisine type and course
- Diet type tag (Vegetarian, Diabetic Friendly etc.)
- Prep time and cook time
- Servings and portion size
- Full ingredient list with quantities
- Step by step cooking instructions
- Complete nutrition breakdown per serving
- Similar recipes (AI suggested alternatives)
- Doctor's note if attached (Tier 2)

**Why this matters:** Patients are more likely to cook something when they have clear, visual, step-by-step guidance. A meal plan without recipe detail is just a word document.

---

### What Patient CANNOT Do — The Hard Boundaries

- ❌ Cannot see any other patient's data — ever
- ❌ Cannot see the doctor's clinical notes about them (only patient-facing notes)
- ❌ Cannot modify their own meal plan directly — they log what they ate, doctor modifies the plan (Tier 2)
- ❌ Cannot access doctor's dashboard or any doctor function
- ❌ Cannot see how many other patients their doctor has
- ❌ Cannot contact admin directly — support goes through the app's help section
- ❌ Cannot extend their own subscription — only doctor can trigger this
- ❌ Cannot change medical conditions without confirmation (safety rule)
- ❌ Cannot remove mandatory allergy selections without a warning step

---

### Patient's Daily Workflow — How It All Connects

```
Morning — Opens app
               ↓
       Sees breakfast recommendation
               ↓
       Views recipe, cooks breakfast
               ↓
       Logs breakfast as eaten
       (or logs what they actually had)
               ↓
       Logs morning water intake
               ↓
       Lunchtime — sees lunch recommendation
               ↓
       Logs lunch
               ↓
       Evening — logs steps count
               ↓
       Dinner — sees recommendation
               ↓
       Logs dinner
               ↓
       Night — logs final water intake
               ↓
       Sees today's nutrition summary
               ↓
       Checks weight progress graph
               ↓
       Sees tomorrow's breakfast already
               ↓
       Logs off — daily routine complete
```

The whole interaction is 2–3 minutes spread across the day. No friction. No complexity. Patient just follows along.

---

### Tier 1 vs Tier 2 — Side by Side Final Comparison

| Feature | Tier 1 Free | Tier 1 Premium (Phase 2) | Tier 2 Doctor Connected |
|---|---|---|---|
| AI meal recommendations | ✅ Basic | ✅ Advanced | ✅ Doctor refined |
| BMI / BMR / TDEE | ✅ | ✅ | ✅ |
| Meal logging | ✅ | ✅ | ✅ |
| Water / steps / weight tracking | ✅ | ✅ | ✅ |
| Full recipe details | ✅ | ✅ | ✅ |
| Weekly ingredient checklist | ✅ | ✅ | ✅ |
| Nutrition insights | ✅ Basic | ✅ Full | ✅ Full + personalised |
| Progress history beyond 30 days | ❌ | ✅ | ✅ |
| Doctor reviewed plan | ❌ | ❌ | ✅ |
| Doctor notes on meals | ❌ | ❌ | ✅ |
| Custom doctor-added recipes | ❌ | ❌ | ✅ |
| Find a Doctor feature | ✅ | ✅ | ❌ not needed |
| Subscription managed by doctor | ❌ | ❌ | ✅ |
| Price to patient | ₹0 | ₹149/month | ₹0 directly |

---

### Summary — Patient in One Simple Picture

```
          PATIENT
              │
   ┌──────────┼───────────┐
   │          │           │
 Sees      Logs        Tracks
 Meals     Reality     Progress
   │          │           │
Weekly     What they   Weight
meal plan  actually    Water
Recipes    ate vs      Steps
Shopping   recommended Adherence
list           │        graphs
               ↓
         System learns
         and adapts
         next week's
         plan
               │
         Doctor sees
         everything
         (Tier 2 only)
         and refines
```

Patient's world is intentionally simple. No complexity. No settings to configure. No dashboards to understand. Open app → see what to eat → log what you ate → track your progress → repeat.

---

Now we have all three roles fully defined. Admin controls everything. Doctor manages their patients. Patient follows their plan. Every boundary is clear. Every feature is justified.

Shall we now go straight into writing the PRD?