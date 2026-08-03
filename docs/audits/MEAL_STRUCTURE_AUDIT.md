# Meal Structure Audit

**Date:** 2026-06-01  
**Scope:** Database → Backend → API → Doctor Dashboard → Patient App  
**Method:** Read-only. No code changes.

---

## THE CORE FINDING

**Answer: Option B — one combined record with a concatenated string.**

When the meal plan generator creates a breakfast with three dishes, it joins them into a single `"Sooji Halwa Breakfast Bowl + Curd chutney + Chai/Coffee/Milk"` string and stores that string as one field inside a JSONB object. There is no dish-level record, no sub-slot ID, and no `food_id` stored in the generated plan. The entire architecture — database, API, both frontends — treats each meal slot as a single atomic unit with a text name. Individual dish editing is architecturally impossible without a schema change.

---

## DATABASE STRUCTURE

**Relevant table:** `recommendations`  
**Plan storage column:** `meals` (JSONB array, `NOT NULL`)

Each element of the `meals` array is one meal slot dict. From Priya's active plan (recommendation id=128, patient_id=5, week_start=2026-05-24):

```
All keys in every meal dict:
['Date', 'Diet Type', 'Ingredients Scaling', 'Meal Type', 'Menu Names',
 'Region', 'Total Calories', 'Total Carbs', 'Total Fat', 'Total Fiber', 'Total Protein']
```

**No `food_id` field exists in any of the 35 stored meal dicts.**

### Raw breakfast entry (May 24, 2026 — exact DB output):

```json
{
  "Date": "2026-05-24",
  "Region": "West",
  "Diet Type": "Vegetarian",
  "Meal Type": "Breakfast",
  "Total Fat": 31.93,
  "Menu Names": "Sooji Halwa Breakfast Bowl + Curd chutney + Chai/Coffee/Milk",
  "Total Carbs": 40.99,
  "Total Fiber": 0.52,
  "Total Protein": 6.63,
  "Total Calories": 443.95,
  "Ingredients Scaling": {
    "Milk": 207.45,
    "curd": 121.63,
    "Sooji": 98.29,
    "Cane sugar": 117.71,
    "Cashew nuts": 17.66,
    "Cardamom powder": 2.94
  }
}
```

All five meal slots for May 24:

| Meal Type      | Menu Names stored |
|----------------|-------------------|
| Breakfast      | `"Sooji Halwa Breakfast Bowl + Curd chutney + Chai/Coffee/Milk"` |
| MorningSnacks  | `"Wheat Grass Shikanji"` |
| Lunch          | `"Curd Oats + Besan Tikki Sabzi + Beetroot Paneer + Chaas"` |
| EveningSnacks  | `"Methi Pakoras"` |
| Dinner         | `"Gujarati Vaghareli Mag + Dal Tadka + Dill Cucumber Raita + Masala chaas"` |

**Clear answer: one record per meal slot. Multiple dishes within a slot are concatenated into one string.**

`Ingredients Scaling` merges all ingredient quantities from all sub-dishes into a single flat dict — you cannot tell which ingredient came from which dish.

---

## MEAL GENERATOR OUTPUT

**File:** `app/services/meal_generator/meal_generator.py`

### How dishes are assembled (lines 371–437):

The generator initializes each meal slot as:

```python
meal_option = {
    "Date": date_str,
    "Meal Type": meal_type,
    "Diet Type": query_diet,
    "Region": region,
    "Total Calories": 0.0,
    "Total Protein": 0.0,
    "Total Carbs": 0.0,
    "Total Fiber": 0.0,
    "Total Fat": 0.0,
    "Menu Names": [],        # starts as a list
    "Ingredients Scaling": {},
}
```

For each sub-slot in the template (grain, accompaniment, beverage...), the generator picks one `FoodItem` from the DB and appends its name:

```python
meal_option["Menu Names"].append(food_item.recipe_name)
```

The `food_item.id` is added to `daily_used_ids` and `weekly_used_ids` but **is never stored in `meal_option`**.

### The combination step (line 437 — critical):

```python
meal_option["Menu Names"] = " + ".join(meal_option["Menu Names"])
```

This is where the list `["Sooji Halwa Breakfast Bowl", "Curd chutney", "Chai/Coffee/Milk"]` becomes the string `"Sooji Halwa Breakfast Bowl + Curd chutney + Chai/Coffee/Milk"`. After this line there is no way to recover which food_item was which sub-slot.

### What gets written to the database (diet_plan_service.py:108–118):

```python
rec = Recommendation(
    patient_id=int(diet_plan.user_id),
    week_start_date=date.today(),
    meals=diet_plan.meals,          # list of meal dicts with Menu Names as string
    ingredient_checklist=diet_plan.ingredient_checklist,
    used_food_ids=diet_plan.used_food_ids,
    is_active=True,
    version=next_version,
)
session.add(rec)
```

`used_food_ids` (stored at the recommendation level) records which food_items were used in the entire plan, but does not map them to individual meal slots or sub-slots.

---

## API LAYER

### GET /api/v1/meal-plan/week (meal_plan.py:111–138)

Returns the `recommendations.meals` JSONB array grouped by date:

```python
for meal in plan.meals:
    day = meal.get("Date")
    if day:
        week.setdefault(day, []).append(meal)
return week
```

Each meal in the response is the raw dict from the database — `Menu Names` is a combined string, no sub-dish breakdown.

### GET /api/v1/doctor/patients/{id}/plan (doctor.py:196–208)

Returns a `RecommendationDetail` with `meals: MealEntry[]` where `MealEntry` is typed as:

```typescript
export interface MealEntry {
  Date: string;
  'Meal Type': string;
  'Menu Names': string;   // combined string, always
  'Diet Type': string;
  'Total Calories': number;
  // ... macros ...
}
```

### PUT /api/v1/doctor/patients/{id}/plan (doctor.py:211–277)

Accepts `PlanOverrideRequest` with `body.meals` — the **entire meals array**. The endpoint replaces `rec.meals` wholesale:

```python
rec.meals = body.meals
```

There is no endpoint that accepts a dish_id, sub-slot identifier, or individual dish replacement. The only editing granularity is the full 35-element meals array.

### No dish-level endpoint exists

Searched entire `app/routers/` for any endpoint that accepts a sub-slot identifier or dish_id. None found.

---

## FRONTEND — DOCTOR DASHBOARD

**File:** `mitihar-frontend/apps/src/app/pages/doctor/patient-tabs/PlanTab.tsx`

### How meal cards render the dish name (line 224–226):

```tsx
<p className="text-sm font-medium text-[#111827] mb-3 leading-snug">
  {meal['Menu Names']}
</p>
```

The full concatenated string is displayed as a single paragraph. No splitting on `" + "`, no individual dish components.

### What the Edit Meal form actually edits (lines 98–147):

The edit form is pre-filled from the meal:

```typescript
const [editForm, setEditForm] = useState({
  name:     meal['Menu Names'],   // the full "Sooji Halwa + Curd chutney + Chai" string
  calories: String(Math.round(meal['Total Calories'])),
  protein:  ..., carbs: ..., fat: ..., fiber: ...,
});
```

On save, it rebuilds the full meals array with the edited combined string:

```typescript
const updatedMeals = allMeals.map(m => {
  if (m.Date === meal.Date && m['Meal Type'] === meal['Meal Type']) {
    return {
      ...m,
      'Menu Names':     editForm.name.trim(),   // still the combined string
      'Total Calories': parseFloat(editForm.calories) || 0,
      // ...
    };
  }
  return m;
});
await doctorApi.overridePlan(patientId, { meals: updatedMeals });
```

The doctor is editing a text box that says `"Sooji Halwa Breakfast Bowl + Curd chutney + Chai/Coffee/Milk"`. There is no dropdown to swap just the chai, no UI to replace just the curd chutney.

### No individual dish editing component exists

Searched entire `PlanTab.tsx` and all patient-tab components. There is no component that splits `Menu Names` on `" + "` to render or edit individual dishes. No sub-dish replacement UI anywhere.

---

## FRONTEND — PATIENT APP

**File:** `mitihar-patient-app/app/meals/meal-detail.tsx`

### How the patient app displays the meal name (line 120):

```tsx
<Text style={s.mealName}>{meal["Menu Names"]}</Text>
```

The full concatenated string is rendered as a single `<Text>` node. A meal named `"Curd Oats + Besan Tikki Sabzi + Beetroot Paneer + Chaas"` is displayed on one line/wrapped block.

### Data structure on the patient side

`meal["Meal Type"]` is used to find the meal in the weekly plan. No dish-level fields exist in the type. The `Meal` type used throughout the patient app maps directly to the same JSONB structure from the database — `Menu Names` is always a combined string.

### Rating system is silently broken

`meal-detail.tsx` line 53:

```typescript
const foodId = meal?.food_id ?? null;
```

Since `food_id` is not stored in meal dicts (confirmed: 0 of 35 meals have this field), `foodId` is always `null`. The condition `showRating = foodId != null && (isPastDay || mealPassedToday)` is therefore always `false`. The thumbs-up / thumbs-down UI is never shown to the patient regardless of time.

Similarly, `DoctorMealOverride` tracking in `doctor.py:76–116` calls `_extract_food_id(meal)` which reads `meal.get("food_id")` — also always `None`. Override diff tracking records `null` food IDs for every override, making the training corpus useless for Phase 8 RL.

---

## ARCHITECTURAL IMPACT

### 1. Can the doctor currently edit individual dishes?

**No.**

The edit form (`editOpen` in `MealCard`) treats the entire `Menu Names` string as one text field. To replace just the chai in breakfast, the doctor must manually retype the entire combined name. There is no UI to swap sub-components, no dropdown, no search-and-replace at the dish level.

### 2. Can the planned adaptive suggestion system (3-4 options per meal slot) be built on this structure?

**No — not without a schema change.**

The adaptive system needs to show: "here are 3 alternatives for the Curd Chutney sub-slot in your Breakfast." This requires knowing:
- Which food_item_id corresponds to each component within a meal slot
- Which sub-slot (grain / accompaniment / beverage) each component fills

Currently neither piece of information is stored. `Menu Names` is an opaque string. `Ingredients Scaling` merges all ingredients together. `food_id` is never written to the meal dict.

### 3. Does the backend need a schema change?

**Yes.** The `meals` JSONB structure must change from meal-level to dish-level. Required change:

**Current structure (one dict per meal slot):**
```json
{
  "Date": "2026-05-24",
  "Meal Type": "Breakfast",
  "Menu Names": "Sooji Halwa Breakfast Bowl + Curd chutney + Chai/Coffee/Milk",
  "Total Calories": 443.95,
  "Ingredients Scaling": { "Milk": 207.45, ... }
}
```

**Required structure (dishes as array within meal slot):**
```json
{
  "Date": "2026-05-24",
  "Meal Type": "Breakfast",
  "Total Calories": 443.95,
  "dishes": [
    {
      "food_id": 1234,
      "recipe_name": "Sooji Halwa Breakfast Bowl",
      "slot_type": "grain",
      "calories": 320.0,
      "protein": 4.5,
      "carbs": 35.0,
      "fat": 14.0,
      "fiber": 0.3,
      "ingredients": { "Sooji": 98.29, "Cane sugar": 117.71, "Cashew nuts": 17.66 }
    },
    {
      "food_id": 567,
      "recipe_name": "Curd chutney",
      "slot_type": "accompaniment",
      ...
    },
    {
      "food_id": 890,
      "recipe_name": "Chai/Coffee/Milk",
      "slot_type": "beverage",
      ...
    }
  ]
}
```

### 4. What is the minimum change needed?

The minimum viable change to unblock dish-level editing:

1. **`meal_generator.py` line 437** — instead of joining, store a `dishes` list:
   ```python
   # Replace: meal_option["Menu Names"] = " + ".join(meal_option["Menu Names"])
   # With: store as structured list, compute combined Menu Names for backward compat display
   meal_option["dishes"] = [{"food_id": fid, "recipe_name": name, "slot_type": slot} ...]
   meal_option["Menu Names"] = " + ".join([d["recipe_name"] for d in meal_option["dishes"]])
   ```
   This keeps backward compatibility for frontends while adding the new structured field.

2. **New API endpoint** — `PATCH /api/v1/doctor/patients/{id}/plan/meals/{date}/{meal_type}/dishes/{dish_index}` accepting a replacement food_item_id or custom name.

3. **Frontend** — doctor dashboard splits `Menu Names` by `" + "` (or reads `dishes` array) to render individual dish cards with swap/replace buttons.

4. **Side fix required:** Store `food_id` in the meal dict per sub-slot at generation time (currently never stored, breaking rating and override tracking).

---

## EFFORT ESTIMATE

**Medium — 2 to 3 sessions.**

| Work | Effort |
|------|--------|
| Generator output format: add `dishes` array per slot while keeping `Menu Names` string for compat | 0.5 sessions |
| New PATCH endpoint for dish-level replacement + update `overridePlan` to accept dish-level changes | 0.5 sessions |
| Doctor dashboard: split dish rendering, swap UI, recipe search per dish | 1 session |
| Patient app: dish-level display + fix rating system (food_id now available) | 0.5 sessions |
| Data migration / backward compat for existing plans | 0.5 sessions |

The generator change is the keystone — everything else falls into place once `dishes` is a structured array. Existing plans without the `dishes` key can fall back to splitting `Menu Names` on `" + "` for display (lossy but acceptable for old plans).

---

## SECONDARY FINDING — RATING AND OVERRIDE TRACKING ARE BROKEN

Not part of the original question but significant enough to flag:

**`food_id` is never stored in meal dicts.** Confirmed on Priya's active plan: 0 of 35 meal entries contain a `food_id` key.

Consequences:
- **Patient rating (Phase 8 Tier 0):** `showRating` in `meal-detail.tsx` evaluates to `false` permanently. Patients never see thumbs-up/thumbs-down. Zero ratings are being collected.
- **DoctorMealOverride tracking:** `_extract_food_id()` in `doctor.py` always returns `None`. All override records have `rejected_food_id=NULL, chosen_food_id=NULL`. The RL training corpus is empty of meaningful signal.

Both issues are fixed automatically by the schema change above (storing `food_id` per dish in the `dishes` array).
