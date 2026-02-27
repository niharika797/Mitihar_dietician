## Screen-by-Screen Breakdown — All Three Roles

---

## 🔵 PATIENT APP (Mobile — React Native)

---

### Onboarding Flow — Tier 1 Standalone

```
Screen 1 → Splash Screen
Screen 2 → Welcome / Landing
Screen 3 → Google OAuth Login
Screen 4 → Health Questionnaire (7 steps)
Screen 5 → Profile Summary + Calculations shown
Screen 6 → Home Dashboard (first plan generating...)
Screen 7 → Home Dashboard (plan ready)
```

---

### Onboarding Flow — Tier 2 Doctor Connected

```
Screen 1 → Splash Screen
Screen 2 → Welcome / Landing
Screen 3 → Google OAuth Login
Screen 4 → "Do you have a doctor?" 
              [ Yes — I was referred ]  [ No — find one / go standalone ]
              
If YES →
Screen 5 → Enter Doctor Code OR Select Doctor from list
Screen 6 → Submit Registration Request
              (name, phone already from Google — just confirm)
Screen 7 → Waiting Screen 
              "Request sent to Dr. Ashok. 
               You'll be notified when approved."
              [ Meanwhile, explore the app in preview mode ]
              
Doctor approves →
Screen 8 → Push notification: "Dr. Ashok approved your request!"
Screen 9 → Health Questionnaire (7 steps — same as Tier 1)
Screen 10 → Profile Summary + BMI/BMR/TDEE shown
Screen 11 → Home Dashboard (plan generating...)
Screen 12 → Home Dashboard (plan ready)
```

---

### Health Questionnaire — Step by Step (Both Tiers)

```
Step 1/7 → Body Metrics
            Height, current weight, target weight, gender, DOB

Step 2/7 → Health Goals
            Primary goal, pace of achievement

Step 3/7 → Medical Conditions
            Multi-select list of 15+ conditions
            "Currently on medication?" toggle

Step 4/7 → Food Allergies ← MANDATORY, cannot skip
            Multi-select with free text field
            "None of the above" option

Step 5/7 → Dietary Preferences
            Diet type, regional preference, meals/day, fasting days

Step 6/7 → Lifestyle
            Activity level, occupation, sleep hours, 
            water intake, smoking/alcohol

Step 7/7 → Current Eating Habits
            Breakfast pattern, outside food frequency,
            fixed meal timing, daily must-have foods

Completion Screen →
            BMI: 24.2 (Normal)
            BMR: 1,680 kcal
            TDEE: 2,310 kcal
            Daily target: 1,850 kcal
            [ View My Meal Plan ]
```

---

### Main App — Patient Screens

```
BOTTOM NAVIGATION BAR (always visible):
[ Home ] [ Meals ] [ Progress ] [ Profile ]
```

---

#### HOME TAB

```
Screen: Home Dashboard
┌────────────────────────────────────┐
│ Good morning, Radha ☀️             │
│ Today's Calories: 320 / 1,850      │
│ ████████░░░░░░░░  17%             │
│                                    │
│ TODAY'S MEALS                      │
│ ✅ Breakfast  → Poha with veg      │
│ ○  Lunch      → Dal + 2 Rotis      │
│ ○  Dinner     → Palak Paneer       │
│                                    │
│ QUICK LOG                          │
│ [ 💧 Log Water ]  [ 👟 Log Steps ] │
│                                    │
│ WEEKLY STREAK                      │
│ 🔥 5 days consistent               │
└────────────────────────────────────┘
```

---

#### MEALS TAB

```
Screen 1: Weekly Meal Plan View
┌────────────────────────────────────┐
│ ← This Week  Feb 25 – Mar 3  →    │
│                                    │
│ MON  TUE  WED  THU  FRI  SAT  SUN │
│  ●    ○    ○    ○    ○    ○    ○  │
│ (today selected)                   │
│                                    │
│ MONDAY, FEB 25                     │
│                                    │
│ 🌅 Breakfast                       │
│ Poha with Vegetables               │
│ 320 cal | P:8g C:52g F:6g         │
│ [ Logged ✓ ]  [ View Recipe ]      │
│                                    │
│ ☀️ Lunch                           │
│ Dal Tadka + 2 Rotis + Raita       │
│ 520 cal | P:22g C:68g F:9g        │
│ [ Log Meal ]  [ View Recipe ]      │
│                                    │
│ 🌙 Dinner                          │
│ Palak Paneer + 1 Roti             │
│ 410 cal | P:18g C:35g F:14g       │
│ [ Log Meal ]  [ View Recipe ]      │
└────────────────────────────────────┘

Screen 2: Recipe Detail Page
┌────────────────────────────────────┐
│ ← Back                             │
│ [Food Image]                       │
│ Poha with Vegetables               │
│ 🥗 Vegetarian  •  🍽 Breakfast    │
│ ⏱ 10 min prep  •  🍴 1 serving    │
│                                    │
│ NUTRITION                          │
│ Cal: 320  Protein: 8g             │
│ Carbs: 52g  Fat: 6g  Fiber: 4g    │
│                                    │
│ INGREDIENTS                        │
│ • Poha (flattened rice) — 60g     │
│ • Onion — 40g                     │
│ • Green peas — 30g                │
│ • Mustard seeds — 2g              │
│ ...                                │
│                                    │
│ INSTRUCTIONS                       │
│ 1. Wash poha and drain...          │
│ 2. Heat oil, add mustard seeds...  │
│                                    │
│ 📝 Doctor's Note (Tier 2 only)     │
│ "Have with a glass of warm water"  │
│                                    │
│ [ ✅ I Had This ]  [ 🔄 I Had Something Else ]
└────────────────────────────────────┘

Screen 3: Log Actual Meal (when tapping "I Had Something Else")
┌────────────────────────────────────┐
│ ← What did you have?               │
│                                    │
│ 🔍 Search food...                  │
│                                    │
│ RECENT                             │
│ • Upma                             │
│ • Bread + Eggs                     │
│                                    │
│ Or type custom food name           │
│ [________________________]         │
│                                    │
│ Portion size:                      │
│ [ Half ]  [ Full ]  [ Double ]     │
│                                    │
│ Time eaten: 8:30 AM  ✏️            │
│                                    │
│ Note (optional):                   │
│ [________________________]         │
│                                    │
│ [ Save Log ]                       │
└────────────────────────────────────┘

Screen 4: Shopping List / Ingredient Checklist
┌────────────────────────────────────┐
│ ← This Week's Shopping List        │
│                                    │
│ VEGETABLES                         │
│ ☐ Spinach (Palak) — 400g          │
│ ☐ Onion — 300g                    │
│ ☐ Tomato — 250g                   │
│ ☑ Green peas — 150g               │
│                                    │
│ GRAINS                             │
│ ☐ Poha — 180g                     │
│ ☐ Whole wheat atta — 500g         │
│                                    │
│ DAIRY                              │
│ ☐ Paneer — 200g                   │
│ ☐ Curd — 300g                     │
│                                    │
│ [ Share List 📤 ]                  │
└────────────────────────────────────┘
```

---

#### PROGRESS TAB

```
Screen 1: Progress Overview
┌────────────────────────────────────┐
│ My Progress                        │
│                                    │
│ WEIGHT JOURNEY                     │
│ Started: 78kg  Current: 74.5kg    │
│ Goal: 68kg                         │
│ [Weight graph — line chart]        │
│ [ + Log Weight ]                   │
│                                    │
│ TODAY                              │
│ 💧 Water: 4 / 8 glasses            │
│ ████░░░░  50%                     │
│ [ + Log Water ]                    │
│                                    │
│ 👟 Steps: 4,230 / 8,000           │
│ █████░░░░  53%                    │
│ [ + Log Steps ]                    │
│                                    │
│ NUTRITION TODAY                    │
│ 830 / 1,850 cal consumed           │
│ ████░░░░░░  45%                   │
│                                    │
│ WEEKLY ADHERENCE                   │
│ 5 of 7 days fully logged           │
│ 71% meal plan followed             │
└────────────────────────────────────┘

Screen 2: Log Water
Screen 3: Log Steps  
Screen 4: Log Weight (with trend note: "Down 0.5kg this week 📉")
Screen 5: Weekly Report
┌────────────────────────────────────┐
│ Week of Feb 25 — Report            │
│                                    │
│ Avg calories/day:  1,720           │
│ Target:            1,850           │
│ Adherence:         93%             │
│                                    │
│ Best day:  Wednesday (100%)        │
│ Missed:    Sunday dinner           │
│                                    │
│ MACROS THIS WEEK (avg/day)         │
│ Protein: 68g  Target: 75g  ⚠️     │
│ Carbs:  220g  Target: 230g  ✅     │
│ Fat:     52g  Target: 55g   ✅     │
│                                    │
│ 💡 You've been low on protein.    │
│ Try adding dal or paneer to meals. │
└────────────────────────────────────┘
```

---

#### PROFILE TAB

```
Screen 1: Profile Overview
┌────────────────────────────────────┐
│ Radha Sharma                       │
│ [Profile photo]                    │
│ Connected to Dr. Ashok (Tier 2)   │
│                                    │
│ MY STATS                           │
│ Height: 162cm   Weight: 74.5kg    │
│ BMI: 28.4       BMR: 1,520 kcal   │
│ TDEE: 2,090 kcal                  │
│                                    │
│ SUBSCRIPTION                       │
│ Active until: March 31 ✅          │
│                                    │
│ SETTINGS                           │
│ › Edit Profile                     │
│ › Update Health Info               │
│ › Notification Preferences         │
│ › Find a Doctor (Tier 1 only)      │
│ › Disclaimer & Privacy             │
│ › Request Account Deletion         │
│ › Logout                           │
└────────────────────────────────────┘

Screen 2: Find a Doctor (Tier 1 only)
┌────────────────────────────────────┐
│ ← Doctors Near You                 │
│ 📍 Mumbai, Maharashtra             │
│                                    │
│ ┌──────────────────────────────┐  │
│ │ Dr. Ashok Mehta              │  │
│ │ Dietician & Nutritionist     │  │
│ │ 📍 2.3 km — Andheri West    │  │
│ │ Speaks: Hindi, English       │  │
│ │ [ Send Request ]             │  │
│ └──────────────────────────────┘  │
│                                    │
│ ┌──────────────────────────────┐  │
│ │ Dr. Priya Shah               │  │
│ │ Clinical Nutritionist        │  │
│ │ 📍 4.1 km — Bandra           │  │
│ │ Speaks: Hindi, Gujarati      │  │
│ │ [ Send Request ]             │  │
│ └──────────────────────────────┘  │
└────────────────────────────────────┘

Screen 3: Notification Preferences
Screen 4: Edit Profile
Screen 5: Update Health Info (re-opens questionnaire sections selectively)