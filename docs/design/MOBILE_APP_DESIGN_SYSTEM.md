# MITYAHAR — Mobile App Design System
> Platform: React Native (Expo SDK 54) · Styling: NativeWind v4
> Scope: Patient App — 36 screens across Auth, Onboarding, Home, Meals, Progress, Profile
> Status: Design System v1 — Ready for Google Stitch screen generation
> Brand identity: Verdant (same as web dashboard — adapted for mobile)

---

## READING THIS DOCUMENT

This document is structured to be used in two ways:
1. **For Google Stitch:** Each screen section contains a precise ASCII wireframe + component spec.
   Paste the section for the screen you want into Stitch and generate from it.
2. **For developers (NativeWind + Expo Router):** Every token, spacing value, and component
   pattern maps directly to a NativeWind utility class or a React Native primitive.

---

## 1. Design Philosophy — Mobile Adaptation

The web dashboard is built for clinical professionals making decisions at a desk.
The patient app is built for a person standing in their kitchen at 7am deciding what to eat.

**Three mobile-specific principles:**

**1. One task per screen, one action per moment.**
Every screen has exactly one primary action. No screen should leave the patient
wondering "what do I do here?" The answer must be obvious within one second.

**2. Frictionless daily ritual.**
The app needs to feel like checking WhatsApp — effortless, fast, familiar.
Total daily interaction: 2–3 minutes. Every extra tap is a broken promise.
Use progressive disclosure: show only what's needed now, reveal depth on demand.

**3. Warm authority.**
Web dashboard = clinical restraint. Patient app = warm, encouraging, Indian-contextual.
Same Verdant green, same Inter font — but more whitespace, softer rounded corners,
celebratory moments (streak, weight loss), and copy that sounds like a caring nutritionist,
not a hospital admission form.

---

## 2. Color System — Verdant (Mobile Tokens)

Same palette as web, different usage priorities for mobile.

```
BRAND GREEN (Primary)
  brand-600:  #1E7C45   ← Primary buttons, active tab, filled progress
  brand-500:  #23924F   ← Pressed states on buttons
  brand-400:  #34B164   ← Success badges, streaks, "logged" indicators
  brand-200:  #A7F3D0   ← Soft tint for calorie progress bar fill
  brand-100:  #DCFCE7   ← Selected card background, onboarding step active
  brand-50:   #F0FDF4   ← Screen background tint on key screens

NEUTRAL (Warm Slate — NOT cold grey)
  slate-900:  #111827   ← Primary text (headings, body)
  slate-700:  #374151   ← Secondary text (descriptions, labels)
  slate-500:  #6B7280   ← Tertiary text (timestamps, placeholders)
  slate-300:  #D1D5DB   ← Dividers, inactive borders
  slate-200:  #E5E7EB   ← Card borders, input borders
  slate-100:  #F3F4F6   ← Background of tapped row states
  slate-50:   #F9FAFB   ← Default screen background (NOT pure white)
  white:      #FFFFFF   ← Cards, bottom sheet surfaces, modals

SEMANTIC
  red-600:    #DC2626   ← Errors, missed day indicators, critical alerts
  red-100:    #FEE2E2   ← Error background pill
  amber-500:  #F59E0B   ← Expiry warnings, sub-optimal adherence
  amber-100:  #FEF3C7   ← Warning pill background
  blue-600:   #2563EB   ← Info states, water icon color
  blue-100:   #DBEAFE   ← Water progress fill (water = blue always)

NUTRITION MACRO COLORS (consistent across all charts and pills)
  protein:    #1E7C45   ← Brand green (protein is primary macro)
  carbs:      #F59E0B   ← Amber
  fat:        #9333EA   ← Purple
  fiber:      #2563EB   ← Blue
  calories:   #111827   ← Near-black (total calorie number is always darkest)

CHART COLORS
  weight-line: #1E7C45  ← Weight history line
  calorie-bar: #34B164  ← Daily calorie bar chart
  target-line: #D1D5DB  ← Target/goal reference line (always muted)
  water-bar:   #2563EB  ← Water intake bars
```

### Mobile Color Rules
- Screen background: always `#F9FAFB` (slate-50), never pure white — reduces eye strain
- Cards (content surfaces): always `#FFFFFF` white with `#E5E7EB` 1px border
- Bottom tab bar background: `#FFFFFF` with top border `#E5E7EB`
- No gradients on interactive elements — gradients on decorative banners only
- Streak fire icon: amber, always. Never brand green for streaks.
- "Logged ✓" state: brand-400 green checkmark, brand-50 background

---

## 3. Typography

```
FONT FAMILY
  All text:    Inter (loaded via @expo-google-fonts/inter)
  Numbers:     Inter with fontVariant: ['tabular-nums'] — prevents layout shift

TYPE SCALE (React Native fontSize values)
  Display:      32px  fontWeight: '700'  → Screen welcome headlines
  Heading 1:    24px  fontWeight: '600'  → Page titles ("My Progress")
  Heading 2:    18px  fontWeight: '600'  → Section headers ("Today's Meals")
  Heading 3:    16px  fontWeight: '600'  → Card titles, meal names
  Body:         14px  fontWeight: '400'  → Default text everywhere
  Body Medium:  14px  fontWeight: '500'  → Labels, list item secondary text
  Caption:      12px  fontWeight: '400'  → Timestamps, helper text, tags
  Micro:        11px  fontWeight: '500'  → Pill labels, badges, tab labels

STAT NUMBERS (dashboard counters)
  Large stat:   36px  fontWeight: '700'  tabular-nums → "1,850" (calorie target)
  Medium stat:  28px  fontWeight: '700'  tabular-nums → "74.5" (weight)
  Small stat:   20px  fontWeight: '600'  tabular-nums → "320 cal" (meal)

LINE HEIGHT
  Body text:    1.5x fontSize (auto in RN)
  Headings:     1.2x fontSize
  Stat numbers: 1.0x (tight — no extra space)
```

### Typography Rules for Mobile
1. Cap line length at ~38 chars for body text (comfortable thumb-width reading)
2. Never use fontWeight: '400' for anything interactive — use '500' minimum on tappable text
3. Calorie numbers are always the largest number on a screen — they anchor the visual hierarchy
4. Diet type tags ("Vegetarian", "Diabetic-Friendly") are always sentence-case, never ALL CAPS
5. Indian food names use their original spelling — "Poha" not "Beaten Rice Dish"

---

## 4. Spacing & Layout System

```
BASE UNIT: 4px

Spacing scale (NativeWind → React Native):
  space-1:  4px    → Tight internal padding (icon to label gap)
  space-2:  8px    → Between related items (meal name + calories)
  space-3:  12px   → Card internal padding (small)
  space-4:  16px   → Standard card padding, list item padding
  space-5:  20px   → Screen horizontal padding
  space-6:  24px   → Section gap, card bottom margin
  space-8:  32px   → Large section gap (between Progress and Meals sections)
  space-10: 40px   → Tall vertical rhythm (between onboarding steps)

SCREEN LAYOUT
  Horizontal padding: 20px both sides (space-5) — this is the content gutter
  Top safe area:      StatusBar height + 8px extra breathing room
  Bottom safe area:   Bottom tab bar height + iOS home indicator (34px)
  
  Content max-width:  375px viewport assumed (iPhone 14 baseline)
                      Scales to 430px (iPhone Pro Max) via flexbox
  
BORDER RADIUS
  radius-sm:   8px   → Input fields, small tags
  radius-md:   12px  → Standard cards
  radius-lg:   16px  → Tall cards, bottom sheets
  radius-xl:   24px  → Primary buttons, large CTAs
  radius-full: 9999px → Pills, avatar circles, progress bars

CARD SHADOW (iOS + Android)
  iOS:    shadowColor: '#000', shadowOffset: {width:0, height:1}, 
          shadowOpacity: 0.06, shadowRadius: 4
  Android: elevation: 2
  
  Heavy shadow (bottom sheets, modals):
  iOS:    shadowOpacity: 0.15, shadowRadius: 12
  Android: elevation: 8
```

---

## 5. Navigation Architecture

```
ROOT NAVIGATOR (Expo Router file-based)

app/
  _layout.tsx              ← Root layout (fonts, QueryClient, auth check)
  (auth)/
    _layout.tsx            ← Auth stack (no tab bar)
    login.tsx
    register.tsx
    google-callback.tsx
  (onboarding)/
    _layout.tsx            ← Onboarding stack (progress indicator top, no tab bar)
    personal-info.tsx
    activity-level.tsx
    goals.tsx
    medical-conditions.tsx
    allergies.tsx
    dietary-preferences.tsx
    lifestyle.tsx
    disclaimer.tsx
    complete.tsx           ← Shows BMI/BMR/TDEE summary
  (tabs)/
    _layout.tsx            ← Bottom tab navigator
    index.tsx              ← Home tab
    meals.tsx              ← Meals tab (stack inside)
    progress.tsx           ← Progress tab (stack inside)
    profile.tsx            ← Profile tab (stack inside)
```

### Bottom Tab Bar Design
```
┌─────────────────────────────────────────────────────┐
│  [🏠 Home]  [🍽 Meals]  [📈 Progress]  [👤 Profile] │
│   active      inactive    inactive       inactive    │
└─────────────────────────────────────────────────────┘

Tab bar specs:
  Height:           56px + bottom safe area
  Background:       #FFFFFF
  Top border:       1px #E5E7EB
  Active icon:      24px, brand-600 filled
  Inactive icon:    24px, slate-400 outline
  Active label:     11px, brand-600, fontWeight:'600'
  Inactive label:   11px, slate-400, fontWeight:'400'
  Active indicator: 3px brand-600 pill above icon (2px wide, centered)
  
  Icons (lucide-react-native):
    Home tab:     <Home> filled when active
    Meals tab:    <Utensils> filled when active
    Progress tab: <TrendingUp> filled when active
    Profile tab:  <User> filled when active
```

### Header Pattern
Most screens inside tabs use a custom header (not the default Expo Router header):
```
┌─────────────────────────────────────────────────────┐
│  [← Back]     Screen Title          [Action icon]   │
│  statusBar safe area included                        │
└─────────────────────────────────────────────────────┘

Header specs:
  Height:         56px + status bar
  Background:     #FFFFFF
  Bottom border:  1px #E5E7EB
  Back chevron:   20px, slate-700
  Title:          16px, fontWeight:'600', slate-900, centered
  Right action:   20px icon (optional — filter, add, share)
  
Screens WITHOUT a back button (tab roots): No back chevron, title left-aligned
Screens WITH a back button (nested screens): Back chevron + centered title
```

---

## 6. Core Component Library

### 6.1 Primary Button
```
Visual:
  Background:    brand-600 (#1E7C45)
  Text:          white, 16px, fontWeight:'600'
  Height:        52px (comfortable touch target)
  Border radius: 24px (rounded-xl)
  Width:         100% of container (full width by default)
  
States:
  Default:   bg-brand-600
  Pressed:   bg-brand-700 (scale: 0.97 via Reanimated)
  Loading:   ActivityIndicator (white) replaces text, disabled
  Disabled:  bg-slate-200, text slate-400

Usage: Primary CTA per screen. Max ONE per screen.
```

### 6.2 Secondary Button
```
Visual:
  Background:    transparent
  Border:        1.5px, slate-300
  Text:          slate-700, 16px, fontWeight:'500'
  Height:        52px
  Border radius: 24px

States:
  Pressed: bg-slate-50
  
Usage: Secondary actions ("Skip", "Cancel", "View Plan")
```

### 6.3 Ghost Button / Text Link
```
  No border, no background
  Text: brand-600, 14px, fontWeight:'500'
  Pressed: brand-700
  
Usage: Inline links, "Forgot password?", "Skip for now"
```

### 6.4 Icon Button (circular)
```
  Size:   44x44px circle (WCAG minimum touch target)
  Bg:     slate-100
  Icon:   20px, slate-700
  Pressed: slate-200
  
Usage: Back buttons, close buttons, filter, share
```

### 6.5 Stat Card
```
┌────────────────────────────────────┐
│ [Icon bg-brand-50 40x40 rounded]   │
│                                    │
│ 1,850                              │  ← 36px bold tabular-nums
│ Daily Calorie Target               │  ← 12px slate-500
│ ──────────────────────────         │
│ ↑ Updated today                    │  ← 11px brand-500 (optional delta)
└────────────────────────────────────┘

Specs:
  Card bg:       #FFFFFF
  Border:        1px #E5E7EB
  Radius:        12px
  Padding:       16px
  Icon circle:   40x40, bg-brand-50, icon 20px brand-600
  Stat number:   36px, fontWeight:'700', tabular-nums, slate-900
  Label:         12px, slate-500
  Width:         (screen-40px) / 2 → two per row in a 2-column grid
```

### 6.6 Meal Card (the most used card in the app)
```
┌────────────────────────────────────────┐
│ 🌅 Breakfast                    08:00  │  ← 12px, slate-500
│                                        │
│ Poha with Vegetables                   │  ← 16px, fontWeight:'600', slate-900
│ 320 cal                                │  ← 20px, fontWeight:'600', brand-600
│                                        │
│ P: 8g  •  C: 52g  •  F: 6g  •  Fi: 4g│  ← 12px, slate-500
│                                        │
│ ○ Not logged   [Log Meal] [View Recipe]│  ← 14px buttons
└────────────────────────────────────────┘

Logged state:
│ ✓ Logged       [View]                  │  ← green checkmark, brand-50 bg on card

Doctor note present (Tier 2):
│ 📝 "Have with warm water" — Dr. Ashok  │  ← 12px, italic, slate-500, brand-50 bg strip

Specs:
  Card bg:           #FFFFFF
  Border:            1px #E5E7EB
  Radius:            12px
  Padding:           16px
  Meal time icon:    16px emoji or lucide icon
  "Logged" bg:       brand-50 tint entire card (very subtle)
  Logged checkmark:  brand-400
```

### 6.7 Progress Ring / Circle
```
  Used for: daily calorie %, water %, adherence %
  Size:     80x80px (dashboard widget), 120x120px (progress detail)
  Stroke:   8px
  Track:    slate-200
  Fill:     brand-600 (calories), blue-500 (water), amber-500 (adherence if <70%)
  Center text: percentage value, 20px bold
  Below ring: label, 12px slate-500
```

### 6.8 Progress Bar (linear)
```
  Height:     8px
  Track:      slate-200
  Fill:       brand-400 (default), blue-400 (water), amber-400 (<70%)
  Border radius: 99px (fully rounded ends)
  
  Used with a label row above:
  "Calories  320 / 1,850" — 14px, then bar below
```

### 6.9 Macro Pill (inline nutrition display)
```
  Format: [ P 8g ] [ C 52g ] [ F 6g ]
  Pill:   rounded-full, 6px horizontal padding, 3px vertical
  Colors: protein=brand-100/brand-700, carbs=amber-100/amber-700,
          fat=purple-100/purple-700, fiber=blue-100/blue-700
  Text:   11px, fontWeight:'600'
```

### 6.10 Day Selector (week calendar strip)
```
┌──────────────────────────────────────────────────┐
│  M    T    W    T    F    S    S                  │
│  25   26   27   28   1    2    3                  │
│  ●                                                │  ← active day: brand-600 circle
│       ·                                           │  ← has data: small dot
└──────────────────────────────────────────────────┘

Specs:
  Scroll: horizontal ScrollView, snap to center
  Day column: 44px wide, center-aligned
  Day letter: 11px, slate-500
  Day number: 14px, slate-700
  Active circle: 36x36px, brand-600 bg, white text
  Data dot: 4px, brand-400, below day number
  Inactive pressed: slate-100 bg
```

### 6.11 Section Header (used throughout lists)
```
  "TODAY'S MEALS"           [See All →]
  14px, fontWeight:'600', slate-900, UPPERCASE, tracking: 0.8

  Divider: no line — use 8px space above section header only
```

### 6.12 Empty State
```
  [Illustration — simple line art, brand-colored]
  
  "No meals logged yet"              ← 18px, fontWeight:'600', slate-900
  "Tap a meal below to get started"  ← 14px, slate-500
  
  [Primary CTA button — optional]
  
  Specs: centered vertically in available space, illustration 120px
```

### 6.13 Bottom Sheet (modal tray)
```
  Rises from bottom, overlays content
  Radius:     24px top corners only
  Bg:         #FFFFFF
  Handle:     32x4px, slate-300, centered, 8px from top
  Shadow:     heavy (elevation:8)
  Dismiss:    tap outside OR swipe down
  
  Usage: Log meal confirmation, quick water log, recipe filter, sort options
```

### 6.14 Toast / Snackbar
```
  Appears at BOTTOM, above tab bar, 16px from tab bar top
  Auto-dismiss: 3 seconds
  
  Success: brand-600 bg, white text, checkmark icon — "Meal logged! 🎉"
  Error:   red-600 bg, white text, X icon
  Info:    slate-900 bg, white text
  
  Shape:   rounded-full pill, horizontal padding 20px, height 44px
  Text:    14px, fontWeight:'500'
```

### 6.15 Input Field
```
  Height:     52px
  Bg:         #FFFFFF
  Border:     1.5px slate-200
  Radius:     12px
  Padding:    horizontal 16px
  
  Label above: 14px, fontWeight:'500', slate-700, 8px margin below
  Placeholder: 14px, slate-400
  Active border: 1.5px brand-500
  Error border:  1.5px red-500
  Error msg:     12px, red-600, 6px below field
  
  Password field: eye icon right side (44x44 touch target)
```

### 6.16 OTP / Code Input
```
  6 separate boxes for subscription code entry
  Each box: 48x56px, rounded-md, border 1.5px slate-200
  Active box: brand-500 border
  Filled: slate-900 text, brand-50 bg
  Gap between boxes: 8px
```

### 6.17 Streak Display
```
  🔥 12         ← emoji + number, 28px bold, amber-500
  Day Streak    ← 12px, slate-500
  
  Background: amber-50 pill, rounded-full, padding 8px 16px
  Used in: Home screen top section
```

### 6.18 Status Badge (inline pill)
```
  Active:   brand-100 bg / brand-700 text
  Inactive: slate-100 bg / slate-500 text
  Expiring: amber-100 bg / amber-700 text
  Logged:   brand-100 bg / brand-600 text + ✓
  Missed:   red-100 bg / red-600 text
  Pending:  amber-100 bg / amber-600 text
  
  Shape: rounded-full, 6px vertical 12px horizontal padding, 11px text
```

---

## 7. Onboarding Step Indicator

Used across the 8 onboarding screens (personal-info → disclaimer):
```
  ┌─────────────────────────────────────────┐
  │  Step 3 of 8                            │
  │  ████████████░░░░░░░░░░░░░░░░           │
  │  Medical Conditions                     │
  └─────────────────────────────────────────┘
  
  Progress bar: full width, 4px height, brand-400 fill, slate-200 track
  "Step X of 8": 12px, slate-500, above bar
  Screen name: 20px, fontWeight:'600', slate-900, below bar
  
  Back button: top-left, 44x44 icon button
  Skip button: top-right, text link — only on non-mandatory steps
               (Allergies and Disclaimer cannot be skipped)
```

---

## 8. Screen-by-Screen Design Specifications

---

### AUTH SCREENS (3 screens)

---

#### Screen A1: Login

```
LAYOUT: Centered single-column, no tab bar, no header
BACKGROUND: white (exception — auth screens are white, not slate-50)

┌──────────────────────────────────────────┐
│                                          │
│        [Mityahar logo — 80px]            │
│        "Mityahar"  24px bold brand-600   │
│        "Your personal diet companion"    │
│         14px slate-500                   │
│                                          │
│        ─────────────────────            │
│                                          │
│  Email                                   │
│  [________________________]              │
│                                          │
│  Password                                │
│  [________________________] [👁]         │
│                                          │
│           Forgot password?               │
│                                          │
│  [        Sign In         ]              │  ← Primary button, brand-600
│                                          │
│  ─────── or continue with ────────      │
│                                          │
│  [🇬 Continue with Google]               │  ← White bg, slate-900 border, 52px
│                                          │
│  Don't have an account? Register         │
│   14px slate-500 + brand-600 link        │
│                                          │
└──────────────────────────────────────────┘

NOTES:
- Logo area: 80px illustration of a leaf + plate (Mityahar brand mark)
- Google button: white background, #E5E7EB border, Google 'G' logo SVG
- "Forgot password?" aligns right, 12px, brand-600
- Keyboard avoiding view: form shifts up when keyboard appears
```

---

#### Screen A2: Register

```
LAYOUT: Scroll view (content may overflow on small screens)
BACKGROUND: white

┌──────────────────────────────────────────┐
│  ← Back                                  │
│                                          │
│  Create Account          24px bold       │
│  Start your diet journey today           │
│  14px slate-500                          │
│                                          │
│  Full Name                               │
│  [________________________]              │
│                                          │
│  Email Address                           │
│  [________________________]              │
│                                          │
│  Password                                │
│  [________________________] [👁]         │
│  Must be 8+ characters                   │  ← 12px slate-400
│                                          │
│  Doctor Code (optional)                  │
│  [________________________]              │
│  "Have a code from your doctor?          │  ← 12px slate-400
│   Enter it here to connect directly."   │
│                                          │
│  [      Create Account      ]            │  ← Primary button
│                                          │
│  ─────── or ─────────────────           │
│                                          │
│  [ 🇬 Continue with Google ]             │
│                                          │
│  Already have an account? Sign In        │
│                                          │
└──────────────────────────────────────────┘

NOTES:
- Doctor Code field is collapsible — starts hidden, "Have a doctor code? +" expands it
- Password strength indicator: 4 dots below field (weak/fair/good/strong) — dot fills brand-600
```

---

#### Screen A3: Google OAuth (handled by Expo Auth Session — no custom UI needed)

```
System Google OAuth sheet appears over the app.
Post-success: redirect to onboarding OR home based on profile_complete flag.
```

---

### ONBOARDING SCREENS (8 screens)

All onboarding screens share the same shell:

```
SHELL:
  Status bar (safe area)
  Step indicator bar (full width, 60px total with padding)
  Screen title (20px bold, 16px below indicator)
  Scrollable content area
  Fixed bottom button area (Primary button, optional Skip)
```

---

#### Screen O1: Personal Info (Step 1 of 8)

```
┌──────────────────────────────────────────┐
│ ← Step 1 of 8  [████░░░░░░░░░░░░░░░░]   │
│ Personal Information                     │
│                                          │
│  Date of Birth                           │
│  [  DD  ]  [   MM   ]  [  YYYY  ]       │  ← 3 dropdowns in a row
│                                          │
│  Gender                                  │
│  [ Male ] [ Female ] [ Other ]           │  ← Segmented control, 3 options
│  Selected: brand-600 bg, white text      │
│  Unselected: white bg, slate-300 border  │
│                                          │
│  Height (cm)                             │
│  [________]  cm                          │
│                                          │
│  Current Weight (kg)                     │
│  [________]  kg                          │
│                                          │
│  Target Weight (kg)                      │
│  [________]  kg                          │
│  "What's your goal weight?"  12px help   │
│                                          │
│  [       Continue →       ]              │
└──────────────────────────────────────────┘
```

---

#### Screen O2: Activity Level (Step 2 of 8)

```
┌──────────────────────────────────────────┐
│ ← Step 2 of 8  [████████░░░░░░░░░░░░]   │
│ How Active Are You?                      │
│  14px slate-500: "This helps calculate   │
│  your daily calorie needs"               │
│                                          │
│  ┌────────────────────────────────────┐  │  ← Tappable option card
│  │ 🪑 Sedentary                       │  │
│  │ Little or no exercise, desk job    │  │  ← 12px slate-500
│  └────────────────────────────────────┘  │
│  ┌────────────────────────────────────┐  │  ← Selected: brand-50 bg + brand-600 border
│  │ 🚶 Lightly Active        ✓         │  │
│  │ Light exercise 1–3 days/week       │  │
│  └────────────────────────────────────┘  │
│  ┌────────────────────────────────────┐  │
│  │ 🏃 Moderately Active               │  │
│  │ Moderate exercise 3–5 days/week    │  │
│  └────────────────────────────────────┘  │
│  ┌────────────────────────────────────┐  │
│  │ 🏋️ Very Active                     │  │
│  │ Hard exercise 6–7 days/week        │  │
│  └────────────────────────────────────┘  │
│  ┌────────────────────────────────────┐  │
│  │ 🔥 Super Active                    │  │
│  │ Very intense daily or twice daily  │  │
│  └────────────────────────────────────┘  │
│                                          │
│  [       Continue →       ]              │
└──────────────────────────────────────────┘

OPTION CARD SPECS:
  Height: 72px, radius:12px, bg:white, border:1.5px slate-200
  Selected: border brand-500, bg brand-50
  Icon: 24px left, 16px from left edge
  Title: 15px fontWeight:'600' left of icon
  Subtitle: 12px slate-500
  Checkmark: 20px brand-600, right side (appears only when selected)
```

---

#### Screen O3: Health Goals (Step 3 of 8)

```
┌──────────────────────────────────────────┐
│ ← Step 3 of 8  [████████████░░░░░░░░]   │
│ Your Health Goals                        │
│  "Select all that apply"  12px slate-500 │
│                                          │
│  MULTI-SELECT CHIPS (2 per row):         │
│                                          │
│  [✓ Weight Loss    ] [  Muscle Gain   ]  │
│  [  Manage Diabetes] [  Heart Health  ]  │
│  [  PCOS/PCOD Mgmt ] [  Better Energy ]  │
│  [  Reduce Cholest.] [  Build Stamina ]  │
│                                          │
│  Pace (how fast?)                        │
│  [ Slow & Steady ] [ Moderate ] [ Fast ] │
│  Segmented control — same as gender field│
│                                          │
│  [       Continue →       ]              │
└──────────────────────────────────────────┘

CHIP SPECS:
  Width: (screenWidth - 52px) / 2  (2 per row with gaps)
  Height: 48px
  Radius: 12px
  Unselected: white bg, slate-200 border, slate-700 text
  Selected: brand-100 bg, brand-600 border, brand-700 text, ✓ prepended
  Text: 14px fontWeight:'500'
```

---

#### Screen O4: Medical Conditions (Step 4 of 8)

```
SAME CHIP LAYOUT as Goals screen — 15+ conditions
Includes a "Currently on medication? [Toggle]" at the bottom
"None of the above" chip clears all other selections when tapped.

Special: "None of the above" chip is full-width, at the bottom.
Toggle row specs: "On medication?" label left + Switch right (brand-600 when on)
```

---

#### Screen O5: Food Allergies (Step 5 of 8) — CANNOT SKIP

```
┌──────────────────────────────────────────┐
│ ← Step 5 of 8  [████████████████████░░] │
│ Food Allergies & Intolerances            │
│  ⚠️ "This is mandatory — affects your   │  ← amber-50 banner, amber-700 text
│  meal plan's safety. Select all that     │    radius:8px, 12px text, full width
│  apply, including 'None' if clear."      │
│                                          │
│  CHIPS (same grid as O3):                │
│  [Dairy / Lactose] [Gluten          ]    │
│  [Tree Nuts      ] [Shellfish/Fish  ]    │
│  [Eggs           ] [Soy             ]    │
│  [Nightshades    ] [Peanuts         ]    │
│                                          │
│  Other (specify):                        │
│  [________________________]              │  ← free text input
│                                          │
│  [✓ None of the above     ] ← full width│
│                                          │
│  [       Continue →       ]              │
│  (disabled until at least 1 chip OR     │
│   "None" selected — no skip allowed)     │
└──────────────────────────────────────────┘
```

---

#### Screen O6: Dietary Preferences (Step 6 of 8)

```
Multi-section scrollable form:

  Diet Type (option cards, single select):
    Vegetarian / Non-Vegetarian / Eggetarian / Vegan / Jain

  Regional Preference (option cards, single select):
    North Indian / South Indian / East Indian / West Indian

  Meals Per Day (segmented control):
    [ 3 meals ] [ 5 meals (with snacks) ]

  Fasting Days (multi-select chips, days of week):
    [ Mon ] [ Tue ] [ Wed ] [ Thu ] [ Fri ] [ Sat ] [ Sun ]
    Below: "None" option

  [Continue →]
```

---

#### Screen O7: Lifestyle (Step 7 of 8)

```
Form with labelled inputs and toggles:

  Sleep Hours per Night:
    Slider 4–10 hours, large thumb, brand-600 track
    Label: "7 hours" updates live

  Daily Water Intake (glasses):
    [ - ] [ 6 ] [ + ]  ← stepper control, brand-600 buttons
    8px between elements

  Occupation Type: (dropdown selector)
    Desk job / Manual labor / Standing job / Mixed

  Smoking:   [ Off / On toggle ]
  Alcohol:   [ Off / On toggle ]
  
  Non-veg meals/week: (stepper, shows only if non-veg diet)
    [ - ] [ 4 ] [ + ]

  Eating Habits (multi-select chips):
    [Skips Breakfast] [Late Night Eating] [Irregular Meals]
    [Eats Quickly   ] [Large Portions  ] [Stress Eating  ]

  [Continue →]
```

---

#### Screen O8: Disclaimer (Step 8 of 8) — CANNOT SKIP

```
┌──────────────────────────────────────────┐
│ ← Step 8 of 8  [████████████████████]   │
│ Before We Begin                          │
│                                          │
│ ┌────────────────────────────────────┐  │
│ │ DISCLAIMER                         │  │  ← Scrollable box, max-height 280px
│ │                                    │  │     slate-50 bg, slate-200 border
│ │ Mityahar provides nutritional      │  │     12px slate-700 text
│ │ guidance based on your inputs.     │  │
│ │ This is not a substitute for       │  │
│ │ medical advice from a qualified    │  │
│ │ healthcare professional...         │  │
│ │ [Full legal text]                  │  │
│ └────────────────────────────────────┘  │
│                                          │
│  ☑  I have read and agree to the terms  │  ← Checkbox (brand-600 when checked)
│     16px label, slate-900               │
│                                          │
│  [  Accept & Start My Journey  ]        │  ← Disabled until checkbox ticked
└──────────────────────────────────────────┘
```

---

#### Screen O9: Onboarding Complete (Completion Summary)

```
┌──────────────────────────────────────────┐
│                                          │
│       [Animated checkmark — Lottie]      │
│        or static ✓ in brand-600 circle   │
│                                          │
│    "Your Profile is Ready! 🎉"           │  ← 24px bold, brand-600
│    "Here's what we calculated for you"   │  ← 14px slate-500
│                                          │
│ ┌────────────────────────────────────┐  │
│ │  BMI              28.4             │  │  ← 16px label + 28px bold stat
│ │  Category         Overweight       │  │
│ ├────────────────────────────────────┤  │
│ │  BMR (Base Rate)  1,520 kcal/day   │  │
│ │  TDEE (with activity) 2,090 kcal   │  │
│ ├────────────────────────────────────┤  │
│ │  Daily Target     1,650 kcal       │  │  ← Highlighted: brand-50 bg row
│ │  (for weight loss pace: Moderate)  │  │
│ └────────────────────────────────────┘  │
│                                          │
│    [  View My Meal Plan  ]               │  ← Primary button
│                                          │
└──────────────────────────────────────────┘

STATS TABLE SPECS:
  Card: white, 1px slate-200 border, radius:12px, padding:0
  Row: 56px, horizontal padding 16px, flexRow space-between
  Divider: 1px slate-100 between rows
  Highlighted row (daily target): brand-50 bg
```

---

### HOME TAB SCREENS (4 screens)

---

#### Screen H1: Home Dashboard (main daily screen)

```
BACKGROUND: slate-50
TOP SECTION: white card, rounded-b-2xl, shadow-sm

┌──────────────────────────────────────────┐
│ [Status bar]                             │
│                                          │
│ ┌──────────────────────────────────────┐ │  ← white top card
│ │ Good morning, Radha ☀️               │ │  ← 20px fontWeight:'600'
│ │ Monday, March 10                     │ │  ← 13px slate-500
│ │                                      │ │
│ │  [🔥 12 Day Streak]  [📅 Day 24]    │ │  ← streak pill + membership day
│ └──────────────────────────────────────┘ │
│                                          │
│ TODAY'S CALORIES                         │  ← section header
│ ┌──────────────────────────────────────┐ │
│ │   [Circular progress ring 120px]     │ │  ← center: "45%" large
│ │      1,320 consumed                  │ │
│ │      of 1,850 target                 │ │
│ │                                      │ │
│ │  [P 68g] [C 182g] [F 38g]           │ │  ← macro pills row
│ └──────────────────────────────────────┘ │
│                                          │
│ TODAY'S MEALS                            │  ← section header
│ ┌──────────────────────────────────────┐ │
│ │ 🌅 Breakfast    ✓ Logged  320 cal   │ │  ← logged state: brand-50 bg
│ ├──────────────────────────────────────┤ │
│ │ ☀️ Lunch         ○ Not logged        │ │  ← tap to expand
│ │ Dal Tadka + Rotis   520 cal  [Log]  │ │
│ ├──────────────────────────────────────┤ │
│ │ 🌙 Dinner        ○ Not logged        │ │
│ │ Palak Paneer        410 cal  [Log]  │ │
│ └──────────────────────────────────────┘ │
│                                          │
│ QUICK LOG                                │  ← section header
│ ┌──────────┐  ┌──────────┐             │
│ │ 💧 Water │  │ 👟 Steps │             │  ← 2-column grid, square cards
│ │ 4/8 gl   │  │ 3,200    │             │
│ └──────────┘  └──────────┘             │
│                                          │
│ DOCTOR UPDATE (Tier 2 only)              │
│ ┌──────────────────────────────────────┐ │
│ │ 📋 Dr. Ashok updated your plan      │ │  ← brand-50 bg, 12px text
│ │ "Swapped Thursday dinner"    [View] │ │
│ └──────────────────────────────────────┘ │
│                                          │
│ [bottom tab bar]                         │
└──────────────────────────────────────────┘

QUICK LOG CARDS:
  Size: (screenWidth - 52px) / 2 × height 80px
  Bg: white, border 1px slate-200, radius:12px
  Emoji: 24px, centered top
  Value: 16px bold, slate-900
  Tapping opens bottom sheet for logging

MEAL ROW IN LIST:
  Height: 64px, horizontal padding 16px
  Logged row: brand-50 bg, ✓ icon brand-400
  Active row: white bg
  Separator: 1px slate-100
  Time slot label: 12px, slate-400
  Meal name: 14px, fontWeight:'500', slate-900
  Calorie: 14px, brand-600
  "Log" button: compact secondary button 60px wide
```

---

#### Screen H2: Weekly Overview

```
┌──────────────────────────────────────────┐
│ ← Weekly Overview                        │
│                                          │
│  Feb 25 – Mar 3  ←  →                   │  ← week navigator arrows
│                                          │
│  [Day selector strip — 7 days]           │
│  MON active, dots on logged days         │
│                                          │
│  CALORIES THIS WEEK                      │
│  ┌────────────────────────────────────┐  │
│  │ [BarChart 7 bars, 180px tall]      │  │  ← Victory Native BarChart
│  │  Target line: dashed, slate-300    │  │
│  │  Bars: brand-400 (met target)      │  │
│  │        amber-400 (<80% of target)  │  │
│  │        red-300 (missed day)        │  │
│  └────────────────────────────────────┘  │
│                                          │
│  WEEK SUMMARY                            │
│  ┌────────────────────────────────────┐  │
│  │ Avg calories/day   1,720 / 1,850   │  │  ← 2-col layout per row
│  │ Days fully logged  5 of 7          │  │
│  │ Adherence score    71%   [badge]   │  │
│  │ Best day           Wednesday       │  │
│  └────────────────────────────────────┘  │
│                                          │
│  MACROS AVERAGE (this week)              │
│  ┌────────────────────────────────────┐  │
│  │ Protein    68g / 75g   ⚠️ Low     │  │
│  │ [█████████████░]                  │  │
│  │ Carbs     220g / 230g  ✅         │  │
│  │ [████████████████]                │  │
│  │ Fat        52g / 55g   ✅         │  │
│  │ [███████████████]                 │  │
│  └────────────────────────────────────┘  │
│                                          │
└──────────────────────────────────────────┘
```

---

#### Screen H3: Notification Center (placeholder)

```
┌──────────────────────────────────────────┐
│ ← Notifications                    [⋯]  │
│                                          │
│  TODAY                                   │
│  ┌────────────────────────────────────┐  │
│  │ 🟢  Plan Updated by Dr. Ashok      │  │
│  │     "Thursday dinner changed"       │  │
│  │                           2 hr ago │  │
│  ├────────────────────────────────────┤  │
│  │ 🔔  Lunch reminder                 │  │
│  │     "Dal Tadka is up next!"         │  │
│  │                          12:00 PM  │  │
│  └────────────────────────────────────┘  │
│                                          │
│  YESTERDAY                              │
│  [List rows same format]                 │
│                                          │
│  [Empty state if no notifications]       │
│  "You're all caught up! ✅"              │
│                                          │
└──────────────────────────────────────────┘

ROW SPECS:
  Height: 72px, padding 16px
  Unread: white bg, left 3px brand-600 indicator border
  Read: slate-50 bg
  Icon circle: 40x40px, colored by type
  Title: 14px fontWeight:'600', slate-900
  Body: 13px slate-500
  Time: 11px slate-400 right-aligned
```

---

#### Screen H4: Doctor Card

```
STANDALONE SCREEN (from profile or home banner):

┌──────────────────────────────────────────┐
│ ← My Doctor                              │
│                                          │
│ ┌────────────────────────────────────┐  │
│ │  [Avatar 64px]                     │  │
│ │  Dr. Ashok Mehta                   │  │  ← 18px fontWeight:'600'
│ │  Dietician & Nutritionist          │  │  ← 14px slate-500
│ │  🏥 Mehta Nutrition Clinic, Mumbai │  │  ← 13px slate-500
│ └────────────────────────────────────┘  │
│                                          │
│  YOUR CONNECTION                         │
│  ┌────────────────────────────────────┐  │
│  │ Status:        Active ✅           │  │
│  │ Connected:     Jan 15, 2026        │  │
│  │ Plan expires:  Mar 31, 2026        │  │  ← amber if <7 days
│  └────────────────────────────────────┘  │
│                                          │
│  [No Doctor Yet — Tier 1 only]           │
│  ┌────────────────────────────────────┐  │
│  │  🔍 Find a Dietician Near You      │  │  ← brand-50 bg card
│  │  Get a personalized plan from a    │  │
│  │  verified doctor in your area.     │  │
│  │  [ Find a Doctor ]                 │  │  ← primary button inside card
│  └────────────────────────────────────┘  │
│                                          │
└──────────────────────────────────────────┘
```

---

### MEALS TAB SCREENS (6 screens)

---

#### Screen M1: Today's Meal Plan (Meals tab root)

```
┌──────────────────────────────────────────┐
│  Meal Plan                         [📅]  │  ← calendar icon opens week view
│                                          │
│  [Day selector strip — 7 days]           │
│  Today highlighted, brand-600 circle     │
│                                          │
│  MONDAY, MARCH 10                        │  ← 14px fontWeight:'600' slate-700
│  1,250 / 1,850 cal  •  68% complete     │  ← 12px slate-500
│                                          │
│  ┌────────────────────────────────────┐  │
│  │ 🌅 BREAKFAST               320 cal │  │  ← section inside scroll
│  │ Poha with Vegetables               │  │
│  │ [P:8g] [C:52g] [F:6g] [Fi:4g]    │  │
│  │ 📝 "Have with warm water" —Dr.A   │  │  ← brand-50 strip, only if note
│  │             [Log Meal] [View] [✓] │  │
│  └────────────────────────────────────┘  │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │ ☀️ LUNCH                    520 cal │  │
│  │ Dal Tadka + 2 Rotis + Raita        │  │
│  │ [P:22g] [C:68g] [F:9g]            │  │
│  │          [Log Meal] [View Recipe]  │  │
│  └────────────────────────────────────┘  │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │ 🌙 DINNER                  410 cal │  │
│  │ Palak Paneer + 1 Roti              │  │
│  │ [P:18g] [C:35g] [F:14g]           │  │
│  │          [Log Meal] [View Recipe]  │  │
│  └────────────────────────────────────┘  │
│                                          │
└──────────────────────────────────────────┘

SECTION HEADER (inside meal cards):
  "🌅 BREAKFAST  · 320 cal"
  10px, uppercase, fontWeight:'600', slate-500
  Background: slate-50 strip, full card width, height 32px
```

---

#### Screen M2: Week View

```
┌──────────────────────────────────────────┐
│ ← Week Plan                              │
│  Feb 25 – Mar 3  ←  [This Week]  →     │
│                                          │
│  [Day selector strip]                    │
│                                          │
│  Tapping a day BELOW renders that day's  │
│  meals — same layout as M1 but read-only │
│                                          │
│  ← Navigate days with horizontal swipe  │
└──────────────────────────────────────────┘
```

---

#### Screen M3: Meal Detail (Recipe View)

```
┌──────────────────────────────────────────┐
│ ← Back                            [🔖]  │  ← bookmark / save icon
│                                          │
│  [Food Image — 220px tall, full width]   │  ← rounded bottom only, radius 16px
│                                          │
│  Poha with Vegetables                    │  ← 22px fontWeight:'700'
│                                          │
│  [🥗 Vegetarian] [🍽 Breakfast] [S.Indian]│  ← tag pills, slate-100 bg
│                                          │
│  NUTRITION PER SERVING                   │  ← section header
│  ┌────────────────────────────────────┐  │
│  │  [Cal]    [Protein]  [Carbs]       │  │  ← 4-col grid (stat mini cards)
│  │  320      8g         52g           │  │
│  │  Calories Protein    Carbs         │  │
│  │  [Fat]    [Fiber]                  │  │
│  │  6g       4g                       │  │
│  └────────────────────────────────────┘  │
│                                          │
│  INGREDIENTS                             │  ← section header
│  • Poha (flattened rice) — 60g          │  ← 14px slate-700, bullet list
│  • Onion — 40g                          │
│  • Green peas — 30g                     │
│  • Mustard seeds — 2g                   │
│  • Curry leaves — 5 leaves              │
│  • Turmeric — 2g                        │
│                                          │
│  INSTRUCTIONS                            │  ← section header
│  1. Wash poha and drain for 5 min...    │  ← numbered list, 14px
│  2. Heat oil in pan over medium heat... │
│  3. Add mustard seeds, let splutter...  │
│                                          │
│  DOCTOR'S NOTE (Tier 2 only)            │  ← brand-50 bg card, only if note
│  ┌────────────────────────────────────┐  │
│  │ 📝 Dr. Ashok                        │  │
│  │ "Have this with a glass of warm    │  │
│  │ water. Avoid adding sugar."        │  │
│  └────────────────────────────────────┘  │
│                                          │
│ ─────────────────────────────────────── │  ← sticky bottom area
│  [ ✅ I Had This ]   [ 🔄 Had Different ]│
└──────────────────────────────────────────┘

STICKY BOTTOM:
  Bg: white, top border 1px slate-200
  Height: 80px + bottom safe area
  Two buttons, equal width, split by 12px gap
  "I Had This": primary green
  "Had Different": secondary outlined
```

---

#### Screen M4: Plan History

```
┌──────────────────────────────────────────┐
│ ← Plan History                           │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │ 🟢 Current Plan                    │  │  ← green dot = active
│  │ Week of March 10                   │  │  ← 15px fontWeight:'600'
│  │ Generated March 8 · v3             │  │  ← 12px slate-500
│  │                             [View] │  │
│  └────────────────────────────────────┘  │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │ Week of March 3                    │  │
│  │ Generated March 1 · v1             │  │
│  │ Adherence: 72%                     │  │
│  │                             [View] │  │
│  └────────────────────────────────────┘  │
│                                          │
│  [older plans — same card format]        │
│                                          │
└──────────────────────────────────────────┘
```

---

#### Screen M5: Shopping List

```
┌──────────────────────────────────────────┐
│ ← Shopping List               [📤 Share] │
│  This Week: Feb 25 – Mar 3               │
│                                          │
│  12 items needed · 3 already have       │  ← 13px slate-500 summary
│                                          │
│  VEGETABLES                              │  ← section header, slate-400
│  ┌────────────────────────────────────┐  │
│  │ ☐  Spinach (Palak)    400g         │  │  ← unchecked row
│  │ ☐  Onion              300g         │  │
│  │ ☑  Green Peas         150g         │  │  ← checked: strikethrough, slate-400
│  └────────────────────────────────────┘  │
│                                          │
│  GRAINS                                  │
│  ┌────────────────────────────────────┐  │
│  │ ☐  Poha (Flattened Rice)  180g    │  │
│  │ ☐  Whole Wheat Atta       500g    │  │
│  └────────────────────────────────────┘  │
│                                          │
│  DAIRY                                   │
│  ┌────────────────────────────────────┐  │
│  │ ☐  Paneer               200g      │  │
│  │ ☑  Curd (Dahi)          300g      │  │
│  └────────────────────────────────────┘  │
└──────────────────────────────────────────┘

CHECKBOX ROW SPECS:
  Height: 52px, padding 16px
  Checkbox: 22x22px, brand-600 when checked
  Item name: 14px slate-900
  Quantity: 13px slate-500, right aligned
  Checked: text strikethrough, slate-400 text
  Category header: 11px uppercase fontWeight:'600' slate-400, padding-top 16px
```

---

#### Screen M6: Plan Empty State

```
┌──────────────────────────────────────────┐
│  Meal Plan                               │
│                                          │
│                                          │
│     [Illustration: empty bowl + leaf]    │
│              120px                       │
│                                          │
│     Your plan is being prepared          │  ← 18px fontWeight:'600' slate-900
│                                          │
│     Your dietician is reviewing your     │  ← 14px slate-500 centered
│     profile and creating a personalized  │
│     meal plan just for you.              │
│                                          │
│     This usually takes 24–48 hours.      │
│                                          │
│     Meanwhile, explore the recipe        │
│     library to get inspired.             │
│                                          │
│     [  Explore Recipes  ]                │  ← secondary button
│                                          │
└──────────────────────────────────────────┘
```

---

### MEAL LOGGING SCREENS (3 screens)

---

#### Screen L1: Log Meal (bottom sheet, appears from M1/M3)

```
BOTTOM SHEET — rises over the current screen

┌──────────────────────────────────────────┐
│              [handle bar]                │
│  Log Breakfast                           │  ← 18px fontWeight:'600'
│                                          │
│  Meal Type: [Breakfast ▼]               │  ← dropdown, pre-filled
│                                          │
│  Calories Consumed (kcal)                │
│  [__________]                            │  ← numeric keyboard
│                                          │
│  Macros (optional, auto from recipe)    │  ← collapsed by default
│  [+ Expand macro fields]                 │
│  When expanded:                          │
│  Protein [__]  Carbs [__]  Fat [__]     │
│                                          │
│  Notes (optional)                        │
│  [__________________________]            │
│                                          │
│  Date  [Today ▼]   Time  [8:30 AM ✏]   │
│                                          │
│  [       Save Meal Log       ]           │  ← primary button
└──────────────────────────────────────────┘
```

---

#### Screen L2: Log from Plan (pre-filled form)

```
Same as L1 but all fields pre-filled from the recommended meal.
User just confirms or adjusts.

Top of sheet shows:
  ┌───────────────────────────────────────┐
  │ Logging as recommended:               │
  │ Poha with Vegetables — 320 cal        │  ← brand-50 banner, 12px
  └───────────────────────────────────────┘
  
"Had something different?" link opens free-form version.
```

---

#### Screen L3: Edit / Delete Log

```
Same layout as L1 but:
- Pre-filled with logged values
- "Delete" ghost button at bottom (red text)
- Edit only allowed within 24h — shows "Edited at 9:15 AM" timestamp
- Past 24h: show info banner "This log is locked after 24 hours"
```

---

### PROGRESS SCREENS (5 screens)

---

#### Screen P1: Progress Hub

```
┌──────────────────────────────────────────┐
│  My Progress                             │
│                                          │
│  TODAY                                   │
│  ┌──────────────┬──────────────────────┐ │
│  │ 💧 Water     │    4 / 8 glasses     │ │  ← 2-col row card
│  │              │  [████░░░░░]  50%    │ │
│  │   [ + Log ]  │                      │ │
│  └──────────────┴──────────────────────┘ │
│  ┌──────────────┬──────────────────────┐ │
│  │ 👟 Steps     │       3,200          │ │
│  │              │  [████░░░░░]  40%    │ │
│  │   [ + Log ]  │  Goal: 8,000         │ │
│  └──────────────┴──────────────────────┘ │
│  ┌──────────────┬──────────────────────┐ │
│  │ ⚖ Weight    │     74.5 kg          │ │
│  │              │  ↓ 0.5kg this week   │ │  ← brand-400 text (down)
│  │   [ + Log ]  │                      │ │
│  └──────────────┴──────────────────────┘ │
│                                          │
│  WEIGHT JOURNEY                          │
│  ┌────────────────────────────────────┐  │
│  │ Started: 78kg  Current: 74.5kg    │  │  ← 13px rows
│  │ Goal:    68kg  Left:    6.5kg     │  │
│  │                                   │  │
│  │ [Line chart — Victory Native]     │  │  ← 160px tall
│  │  brand-600 line, dots on entries  │  │
│  │  target weight: dashed slate-300  │  │
│  └────────────────────────────────────┘  │
│                                          │
│  STREAK                                  │
│  ┌────────────────────────────────────┐  │
│  │ 🔥 12 Day Streak!                 │  │  ← 20px bold amber-500
│  │ Logged every day this fortnight   │  │  ← 13px slate-500
│  │ [M][T][W][T][F][S][S] ← dots row │  │  ← filled=logged, empty=missed
│  └────────────────────────────────────┘  │
└──────────────────────────────────────────┘
```

---

#### Screen P2: Water Log (bottom sheet)

```
BOTTOM SHEET:

  [handle]
  Log Water Intake      18px fontWeight:'600'
  
  How many glasses today?
  
  [  −  ]  [ 6 ]  [  +  ]    ← large stepper, 48x48 buttons
  Brand-600 buttons, 36px number
  
  Visual: Row of 8 glass icons
  Filled glasses: brand-600 💧
  Empty: slate-200 outline
  
  Fills in real time as counter changes
  
  [ Save ]  ← full width primary button
```

---

#### Screen P3: Steps Log (bottom sheet)

```
  Log Steps Today
  
  [__________]  ← numeric input, large 32px text
  "Today's step count"  12px slate-500
  
  Sync from phone?   [Get from Health App]
  ← ghost button, only if HealthKit/Google Fit available
  
  [ Save ]
```

---

#### Screen P4: Weight Log (bottom sheet)

```
  Log Your Weight
  
  [ 74 ] . [ 5 ] kg    ← two-part stepper or single input
  "Last logged: 74.5kg on March 8"  12px slate-400
  
  ↓ Down 0.3kg since last time    ← brand-400 if down, red-500 if up
  
  [ Save ]
```

---

#### Screen P5: Progress Charts (full screen)

```
┌──────────────────────────────────────────┐
│ ← Weight History            [30d ▾ 90d] │  ← time range selector
│                                          │
│  Current: 74.5 kg  ↓ 3.5kg since start  │  ← 20px bold + 13px
│                                          │
│  ┌────────────────────────────────────┐  │
│  │ [LineChart — Victory Native]       │  │
│  │  Height: 220px                     │  │
│  │  Weight line: brand-600            │  │
│  │  Target line: dashed slate-300     │  │
│  │  Data points: 4px circles          │  │
│  │  Axes: 11px slate-400              │  │
│  │  Grid: horizontal only, slate-100  │  │
│  └────────────────────────────────────┘  │
│                                          │
│  CALORIE TREND (7-day bars)              │
│  ┌────────────────────────────────────┐  │
│  │ [BarChart 7 bars, 160px tall]      │  │
│  └────────────────────────────────────┘  │
│                                          │
└──────────────────────────────────────────┘
```

---

### DOCTOR CONNECTION SCREENS (3 screens)

---

#### Screen D1: Subscription / Activate

```
┌──────────────────────────────────────────┐
│ ← Activate Subscription                  │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │  🏥 Connect to Your Doctor         │  │  ← brand-50 bg card
│  │                                   │  │
│  │  Enter the 12-character code      │  │
│  │  shared by your doctor            │  │
│  │  to activate your subscription.   │  │
│  └────────────────────────────────────┘  │
│                                          │
│  Subscription Code                       │
│  ┌──┐ ┌──┐ ┌──┐ ─ ┌──┐ ┌──┐ ┌──┐     │  ← 6-char segments (or single input)
│  │ A│ │ B│ │ C│   │ 1│ │ 2│ │ 3│     │
│  └──┘ └──┘ └──┘   └──┘ └──┘ └──┘     │
│                                          │
│  [ Activate Subscription ]               │  ← primary button
│                                          │
│  ─────── or ─────────────────           │
│                                          │
│  Don't have a code? Request a doctor.   │  ← link → D2
└──────────────────────────────────────────┘
```

---

#### Screen D2: Request Doctor

```
┌──────────────────────────────────────────┐
│ ← Find a Doctor                          │
│                                          │
│  📍 Mumbai, Maharashtra      [Change]    │  ← location row
│                                          │
│  [🔍 Search doctors...]                  │  ← search input
│                                          │
│  DIETICIANS NEAR YOU                     │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │ [Avatar 48px]  Dr. Ashok Mehta    │  │  ← doctor card
│  │               Dietician            │  │
│  │               📍 2.3km · Andheri  │  │
│  │               Hindi, English       │  │
│  │               [ Send Request ]     │  │
│  └────────────────────────────────────┘  │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │ [Avatar]  Dr. Priya Shah           │  │
│  │           Clinical Nutritionist    │  │
│  │           📍 4.1km · Bandra       │  │
│  │           Hindi, Gujarati          │  │
│  │           [ Send Request ]         │  │
│  └────────────────────────────────────┘  │
│                                          │
└──────────────────────────────────────────┘

DOCTOR CARD SPECS:
  Height: auto (~100px min)
  Padding: 16px
  Avatar: 48px circle, slate-200 bg default
  Name: 15px fontWeight:'600'
  Specialization: 13px slate-500
  Distance + location: 12px slate-400, map pin icon 12px
  Languages: 12px slate-400
  Button: secondary outlined, 120px wide, aligned right
```

---

#### Screen D3: Connection Status

```
PENDING STATE:
┌──────────────────────────────────────────┐
│ ← Request Status                         │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │  ⏳ Request Pending                 │  │  ← amber-50 card, amber-600 text
│  │                                   │  │
│  │  Sent to Dr. Ashok Mehta          │  │
│  │  February 24, 2026                │  │
│  │                                   │  │
│  │  "Your request is with the doctor. │  │
│  │  You'll be notified once approved. │  │
│  │  This usually takes 24 hours."    │  │
│  └────────────────────────────────────┘  │
│                                          │
│  [ Cancel Request ]  ← ghost red button  │
│                                          │
└──────────────────────────────────────────┘

ACCEPTED STATE: brand-50 card, brand-600 ✅ text, "Connected!" headline
REJECTED STATE: red-50 card, red-600 ✗ text, rejection note shown, [Try Another Doctor] CTA
```

---

### PROFILE & SETTINGS SCREENS (4 screens)

---

#### Screen PR1: Profile Overview (Profile tab root)

```
┌──────────────────────────────────────────┐
│  My Profile                        [✏]  │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │  [Avatar 72px]  Radha Sharma       │  │  ← profile header card
│  │                 radha@example.com  │  │
│  │                 Joined Jan 2026    │  │
│  │  [Connected: Dr. Ashok ✅]         │  │  ← status badge
│  └────────────────────────────────────┘  │
│                                          │
│  MY STATS                                │
│  ┌──────────────┬───────────────────┐   │
│  │ Height 162cm │ Weight   74.5 kg  │   │  ← 2-col stat grid
│  ├──────────────┼───────────────────┤   │
│  │ BMI    28.4  │ BMR    1,520 kcal │   │
│  ├──────────────┼───────────────────┤   │
│  │ TDEE 2,090   │ Target 68 kg      │   │
│  └──────────────┴───────────────────┘   │
│                                          │
│  SUBSCRIPTION                            │
│  ┌────────────────────────────────────┐  │
│  │ Status: Active ✅                  │  │
│  │ Expires: March 31, 2026           │  │  ← amber text if <7 days
│  └────────────────────────────────────┘  │
│                                          │
│  SETTINGS LIST                           │
│  ┌────────────────────────────────────┐  │
│  │ 👤 Edit Profile              →     │  │  ← list rows, 52px each
│  ├────────────────────────────────────┤  │
│  │ 🏃 Update Health Info         →    │  │
│  ├────────────────────────────────────┤  │
│  │ 🔔 Notifications              →    │  │
│  ├────────────────────────────────────┤  │
│  │ 📋 Disclaimer & Privacy       →    │  │
│  ├────────────────────────────────────┤  │
│  │ 🗑 Request Data Deletion       →    │  │  ← red-600 text
│  ├────────────────────────────────────┤  │
│  │ 🚪 Logout                          │  │  ← red-600 text, no chevron
│  └────────────────────────────────────┘  │
│                                          │
└──────────────────────────────────────────┘

SETTINGS LIST ROW SPECS:
  Height: 52px, padding 16px
  Icon: 20px left, slate-500
  Label: 14px fontWeight:'500' slate-900
  Chevron: 16px slate-300, right side (absent on Logout)
  Separator: 1px slate-100
```

---

#### Screen PR2: Edit Profile

```
┌──────────────────────────────────────────┐
│ ← Edit Profile              [Save]       │  ← Save in header right
│                                          │
│  [Avatar 72px + 📷 change button]        │
│                                          │
│  Full Name                               │
│  [Radha Sharma______________]            │
│                                          │
│  Phone Number                            │
│  [+91 98765 43210__________]             │
│                                          │
│  Email                                   │
│  [radha@example.com] (read-only)         │  ← slate-100 bg, locked
│                                          │
│  Current Weight (kg)                     │
│  [74.5___]                               │
│  "Updating weight recalculates your      │
│  daily targets"  12px slate-400          │
│                                          │
│  [    Save Changes    ]                  │  ← primary button
└──────────────────────────────────────────┘
```

---

#### Screen PR3: Notification Preferences

```
┌──────────────────────────────────────────┐
│ ← Notifications                          │
│                                          │
│  MEAL REMINDERS                          │  ← section header
│  ┌────────────────────────────────────┐  │
│  │ Breakfast Reminder     [Toggle ✅] │  │
│  │ 8:00 AM             [Change time] │  │
│  ├────────────────────────────────────┤  │
│  │ Lunch Reminder         [Toggle ✅] │  │
│  │ 1:00 PM             [Change time] │  │
│  ├────────────────────────────────────┤  │
│  │ Dinner Reminder        [Toggle ✅] │  │
│  │ 8:00 PM             [Change time] │  │
│  └────────────────────────────────────┘  │
│                                          │
│  HEALTH REMINDERS                        │
│  ┌────────────────────────────────────┐  │
│  │ Water Reminders        [Toggle ✅] │  │
│  ├────────────────────────────────────┤  │
│  │ Weekly Report (Sunday)  [Toggle ✅]│  │
│  ├────────────────────────────────────┤  │
│  │ Inactivity Alerts      [Toggle ✅] │  │
│  └────────────────────────────────────┘  │
│                                          │
│  QUIET HOURS                             │
│  ┌────────────────────────────────────┐  │
│  │ Do Not Disturb         [Toggle ○]  │  │
│  │ 10:00 PM → 7:00 AM                │  │
│  └────────────────────────────────────┘  │
│                                          │
└──────────────────────────────────────────┘

TOGGLE ROW SPECS:
  Height: 52px, padding 16px
  Label: 14px fontWeight:'500' slate-900
  Toggle: right side, brand-600 when on, slate-200 when off
  Sub-label (time): 12px slate-500, below label on same row
```

---

#### Screen PR4: About / Disclaimer

```
┌──────────────────────────────────────────┐
│ ← About & Disclaimer                     │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │  Mityahar  v1.0.0                  │  │  ← brand logo + version
│  │  "Your personal diet companion"    │  │
│  └────────────────────────────────────┘  │
│                                          │
│  LEGAL                                   │
│  ┌────────────────────────────────────┐  │
│  │ [Full disclaimer text — 12px]      │  │  ← scrollable text box
│  │ Mityahar provides nutritional...  │  │
│  │ This is not medical advice...     │  │
│  └────────────────────────────────────┘  │
│                                          │
│  Privacy Policy  →                       │  ← opens webview
│  Terms of Service →                      │
│                                          │
└──────────────────────────────────────────┘
```

---

## 9. Motion & Animation Guidelines (React Native Reanimated 3)

```
PRINCIPLE: Motion communicates — never decorates.
Every animation must answer: "does this help the user understand what just happened?"

DURATIONS:
  Quick (feedback):      150ms   — button press scale, toggle flip
  Standard (transition): 250ms   — bottom sheet enter, screen enter
  Deliberate (context):  350ms   — onboarding step change, celebration
  Never above 400ms on interactive elements.

EASING:
  Enter:    Easing.out(Easing.cubic)   — decelerates, feels arriving
  Exit:     Easing.in(Easing.cubic)    — accelerates, feels leaving
  Spring:   { damping: 15, stiffness: 150 } — for bouncy confirmations

SPECIFIC PATTERNS:

1. Button press:
   withTiming(0.96, {duration: 100}) on scale — subtle feedback
   
2. Meal card "logged" state:
   Scale 1 → 1.02 → 1 in 250ms (spring) + background color shift
   → tells user something was recorded
   
3. Bottom sheet:
   translateY from screenHeight to 0, 300ms, Easing.out(Easing.cubic)
   Backdrop: opacity 0 → 0.5, same duration
   
4. Progress ring:
   Animated stroke draw on mount, 600ms, delay by 200ms
   
5. Streak counter:
   Numbers roll up (like an odometer) on increment, 400ms
   
6. Calorie bar fill:
   Width animates from 0 to value on screen mount, 500ms, eased out
   
7. Onboarding step progress bar:
   Width increases on step advance, 300ms, ease out
   
8. Pull-to-refresh:
   Use default RefreshControl with brand-600 tintColor

AVOID:
  ❌ Continuous ambient animations (spinning logos, pulse rings)
  ❌ Parallax scrolling effects on content
  ❌ Layout animations unless deliberate (Reanimated's Layout prop)
  ❌ Animations on data loading — use skeleton instead
```

---

## 10. Gesture Patterns

```
TAP (most common):
  All interactive elements: 44x44px minimum touch target
  Even if visual element is smaller, add hitSlop={12} around it

SWIPE LEFT on meal log entry:
  Reveals "Delete" action (red, 80px wide)
  Use Swipeable from react-native-gesture-handler
  
SWIPE DOWN on bottom sheet:
  Dismisses the sheet
  
SWIPE LEFT/RIGHT on day selector:
  Navigate to prev/next day
  
SWIPE LEFT/RIGHT on onboarding screens:
  Back swipe should not skip — use onboarding back button only
  Disable back swipe gesture on mandatory screens (allergies, disclaimer)
  
LONG PRESS on meal card:
  Haptic feedback + context menu (Log / View Recipe / Skip Today)
  
PULL TO REFRESH:
  Home tab: refreshes today's summary + meal plan
  Progress tab: refreshes all progress data
```

---

## 11. Accessibility

```
MINIMUM TOUCH TARGET: 44x44px (WCAG 2.5.5)
CONTRAST RATIOS:
  Body text (slate-900 on white):    15.8:1  ✅
  Secondary text (slate-500 on white): 4.6:1 ✅ (large text)
  Brand green on white (#1E7C45):     6.7:1  ✅
  White on brand-600:                 6.7:1  ✅

DYNAMIC TEXT:
  All fontSize values use accessibilityScale — use Tailwind text-sm/base/lg
  Don't fix heights that would clip larger accessibility fonts

SCREEN READER:
  All interactive elements have accessibilityLabel
  Images: accessibilityRole='image' + descriptive label
  Buttons: accessibilityRole='button', accessibilityState for disabled
  Progress indicators: accessibilityValue={{ min:0, max:100, now:45 }}

HAPTICS (Expo Haptics):
  Success log: Haptics.notificationAsync(NotificationFeedbackType.Success)
  Error: Haptics.notificationAsync(NotificationFeedbackType.Error)
  Button press: Haptics.impactAsync(ImpactFeedbackStyle.Light)
```

---

## 12. NativeWind v4 Utility Class Reference

Quick reference — classes used throughout the app:

```
BACKGROUNDS:
  bg-slate-50       ← screen background
  bg-white          ← cards, sheets, tab bar
  bg-brand-600      ← primary buttons, active tab
  bg-brand-50       ← tinted card backgrounds (logged meals)
  bg-brand-100      ← selected chip/option state
  bg-amber-50       ← warning banners
  bg-red-50         ← error banners

TEXT:
  text-slate-900    ← primary text
  text-slate-700    ← secondary text
  text-slate-500    ← placeholder, captions
  text-brand-600    ← links, active labels, calorie numbers
  text-amber-600    ← warnings
  text-red-600      ← errors, delete actions

BORDERS:
  border border-slate-200    ← card outline
  border-1.5 border-slate-300 ← input default
  border-1.5 border-brand-500 ← input active
  border-1.5 border-red-500   ← input error

SPACING (horizontal page padding always px-5):
  px-5   → 20px horizontal (screen gutter)
  py-4   → 16px vertical (card padding)
  gap-3  → 12px gap between items
  gap-4  → 16px gap between cards

ROUNDED:
  rounded-xl   → 12px (cards)
  rounded-2xl  → 16px (large cards, bottom sheets)
  rounded-full → pills, circles

TYPOGRAPHY:
  text-sm      → 14px body
  text-xs      → 12px caption
  text-base    → 16px card title
  text-lg      → 18px section title
  text-xl      → 20px page title
  text-2xl     → 24px large heading
  font-medium  → 500
  font-semibold → 600
  font-bold    → 700
  tabular-nums → for all numeric values
```

---

## 13. What NOT to Build — Mobile Anti-Patterns

| Anti-Pattern | Why Wrong for Mityahar | Better Alternative |
|---|---|---|
| Hamburger menu | Hides primary navigation from users | Bottom tab bar always |
| Onboarding carousel with swipe | Users skip by swiping — miss mandatory inputs | Step-by-step form with Continue button |
| Calorie display only (no macros) | Protein is critical for Indian diets | Always show macro pills alongside calories |
| Full-screen interstitial ads | N/A — product is ad-free | No ads ever |
| Dark mode at launch | +40% dev time, low clinical necessity | Ship light mode only in v1 |
| Search requiring 3+ taps to reach | Doctors want instant patient lookup | Prominent search on list screens |
| Infinite scroll on meal plan | Patients need to see "whole week" at once | Paginated by day/week only |
| Auto-play animations on home load | Distracting for daily use | Mount animations only, no looping |
| Generic green (lime/emerald) | Looks like a gym app | Use exact Verdant palette only |
| Centered body text | Uncomfortable to read on phones | Left-align all body text, center only empty states |
| Bottom sheet stacking (sheets on sheets) | Confusing depth hierarchy | Max 1 sheet at a time |
| Haptics on every interaction | Feels aggressive / battery drain | Haptics only on success, error, and destructive confirm |
| Weight displayed without units | Confusing for kg vs lb | Always show "kg" inline |
| Auto-dismiss alerts | Critical messages (allergy, expiry) need to be read | Persistent banners for critical info |
| Flat list for shopping (no categories) | Hard to use in a supermarket | Always group by ingredient category |

---

## 14. Screen Generation Order (For Google Stitch)

Generate screens in this order — each builds on visual language established by the previous:

```
BATCH 1 — Foundation (establishes color, type, button style)
  1. Login (A1)
  2. Register (A2)
  3. Onboarding Complete — BMI summary (O9)

BATCH 2 — Onboarding (establishes step flow, chips, cards)
  4. Personal Info (O1)
  5. Activity Level (O2) — establishes option card pattern
  6. Health Goals (O3) — establishes chip grid pattern
  7. Food Allergies (O5) — establishes warning banner
  8. Disclaimer (O8) — establishes mandatory screen pattern

BATCH 3 — Core App (establishes card system, tab bar, progress)
  9. Home Dashboard (H1) — most complex screen, defines the whole app feel
  10. Today's Meal Plan (M1)
  11. Meal Detail / Recipe (M3)
  12. Progress Hub (P1)

BATCH 4 — Logging & Interaction
  13. Log Meal Bottom Sheet (L1)
  14. Log Water (P2)
  15. Shopping List (M5)

BATCH 5 — Profile & Secondary
  16. Profile Overview (PR1)
  17. Edit Profile (PR2)
  18. Doctor Connection (D1, D2, D3)
  19. Weekly Overview (H2)
  20. Notification Preferences (PR3)
```

---

## 15. Figma/Stitch Generation Prompt Template

When generating a screen in Google Stitch, use this template:

```
"Design a [SCREEN NAME] screen for Mityahar, an Indian diet planning mobile app.

BRAND: Verdant green (#1E7C45). Background slate-50 (#F9FAFB). Cards white with 
1px #E5E7EB border, 12px radius. Font: Inter throughout.

LAYOUT: [paste the ASCII wireframe from the relevant screen section above]

COMPONENTS NEEDED:
- [list the specific components from Section 6 that appear on this screen]

FEEL: Warm, clinical-adjacent, not gym/fitness aesthetic. Think Notion meets 
a friendly Indian dietician's app. Generous white space. No gradients on buttons. 
No flashy illustrations — simple line art only."
```

---

## Summary — System at a Glance

```
App type:     Patient-facing daily utility (not a medical record system)
Platform:     iOS + Android (React Native, Expo SDK 54)
Navigation:   Bottom tabs (4 tabs) + stack navigators inside each tab
Auth:         Email/password + Google OAuth (Expo Auth Session)
Font:         Inter (expo-google-fonts)
Styling:      NativeWind v4 (Tailwind utility classes)
Colors:       Verdant (#1E7C45 primary), Warm Slate, Semantic (red/amber/blue)
Charts:       Victory Native (weight line, calorie bar, macro stacked bar)
Animation:    React Native Reanimated 3 (purposeful, <400ms)
Gestures:     react-native-gesture-handler (swipe-to-delete, bottom sheet drag)
Storage:      Expo SecureStore (tokens), AsyncStorage (preferences)
API client:   Axios with interceptors (mirrors web dashboard pattern)
State:        Zustand (auth) + TanStack Query v5 (server state)

Total screens: 36
  Auth:              3
  Onboarding:        8 (+ 1 completion)
  Home:              4
  Meals:             6
  Meal Logging:      3
  Progress:          5
  Doctor Connection: 3
  Profile/Settings:  4 (+1 about)
```
