# Weekly Meal Plan Generation — End-to-End Flow

Every claim in this document is backed by a code snippet with file path and line numbers,
verified against the working tree on branch `feature/api-remediation-v0.2` (2026-07-15).

**High-level pipeline:**

```
Patient onboarding (POST /api/v1/patients/onboarding)
        │  stores height/weight/activity/diet/conditions on patients row
        ▼
Entry point (POST /api/v1/diet-plans/generate, or background task after onboarding)
        │  builds user_data dict from the Patient ORM row
        ▼
DietPlanService.generate_diet_plan()          app/services/diet_plan_service.py
        │  adds preferred/avoided food IDs from last week's summary (R-7B)
        ▼
MealGenerator.generate_meal_plan()            app/services/meal_generator/meal_generator.py
        │  BMI/BMR/TDEE → per-meal calorie targets → 7 days × 3 meals ×
        │  slot template × 4 combos per slot, with condition-tag filtering
        ▼
DietPlanService.store_diet_plan()             recommendations + weekly_combos rows (84/week)
```

---

## Section 1: User Input & Calorie Calculation

### 1.1 Where the inputs come from

Patient inputs are collected once at onboarding and validated by a Pydantic schema
(`app/schemas/patients.py:12-39`):

```python
# app/schemas/patients.py:12-33
class OnboardingRequest(BaseModel):
    date_of_birth:        date
    # T4-5: use enums/Literals — reject any value not in the allowed set
    gender:               Literal["Male", "Female", "Other"]
    height_cm:            float          = Field(..., gt=0)
    weight_kg:            float          = Field(..., gt=0)
    activity_level:       ActivityLevel  = ActivityLevel.LIGHTLY_ACTIVE
    diet_type:            DietType       = DietType.VEGETARIAN
    region:               Literal["North", "South", "East", "West"] = "North"
    health_condition:     HealthCondition = HealthCondition.HEALTHY
    # T4-6: bounded list fields — cap item count and per-item length
    health_goals:         BoundedStrList = Field(default_factory=list)
    medical_conditions:   BoundedStrList = Field(default_factory=list)
    food_allergies:       BoundedStrList = Field(default_factory=list)
    ...
    nonveg_meals_per_week: int           = Field(default=0,   ge=0, le=21)
```

The onboarding endpoint (`POST /api/v1/patients/onboarding`,
`app/routers/patients.py:67-124`) computes BMI/BMR/TDEE immediately and stores them
on the `patients` row, then persists all inputs:

```python
# app/routers/patients.py:80-89
    age = _derive_age(body.date_of_birth)

    bmr = calculate_bmr(
        body.gender,
        body.weight_kg,
        body.height_cm,
        age,
    )
    tdee = calculate_tdee(bmr, body.activity_level)
    bmi = calculate_bmi(body.height_cm, body.weight_kg)
```

```python
# app/routers/patients.py:118-120 (inside the UPDATE .values(...))
            bmi=round(bmi, 2),
            bmr=round(bmr, 2),
            tdee=round(tdee, 2),
```

### 1.2 Entry points that build `user_data`

The primary patient-facing entry point is `POST /api/v1/diet-plans/generate`
(`app/routers/diet_plans.py:156-203`). It reads the stored `Patient` row and builds the
`user_data` dict the generator expects:

```python
# app/routers/diet_plans.py:180-203
    # Build user_data dict that meal_generator expects
    user_data = {
        "id": str(current_user.id),
        "email": current_user.email,
        "name": current_user.name,
        "gender": current_user.gender,
        "height": float(current_user.height_cm),
        "weight": float(current_user.weight_kg),
        "activity_level": current_user.activity_level,
        "diet": current_user.diet_type,
        "health_condition": current_user.health_condition or "Healthy",
        "region": current_user.region or "North",
        "nonveg_meals_per_week": current_user.nonveg_meals_per_week or 3,
        "health_goals": list(current_user.health_goals or []),
        "medical_conditions": list(current_user.medical_conditions or []),
        # medical_conditions drives PCOS/Thyroid macro overrides in calculations.py
        # Derive age from date_of_birth; fallback 30 if not set
        "age": (
            date.today().year - current_user.date_of_birth.year
            - ((date.today().month, date.today().day) <
               (current_user.date_of_birth.month, current_user.date_of_birth.day))
            if current_user.date_of_birth else 30
        ),
    }
```

Other call sites that build an equivalent `user_data` and call
`DietPlanService.generate_diet_plan()`:

| Caller | Location | Trigger |
|---|---|---|
| Onboarding background task | `app/routers/patients.py:44` (dict built at `patients.py:158-175`) | fire-and-forget after onboarding 200 |
| Weight log regeneration | `app/routers/progress.py:88` | non-blocking regen after weight log |
| Meal-plan router | `app/routers/meal_plan.py:99` | plan regeneration |
| Doctor-triggered | `app/routers/doctor.py:462`, `app/routers/doctor.py:2686` | doctor dashboard actions |
| Users router | `app/routers/users.py:126` | profile-update regen |

### 1.3 Orchestration layer (`DietPlanService`)

`DietPlanService.generate_diet_plan()` (`app/services/diet_plan_service.py:47-93`) adds
behavioral personalization signals from last week's summary (R-7B), then delegates:

```python
# app/services/diet_plan_service.py:66-82
        if prev_summary and prev_summary.summary_data:
            dish_freq = prev_summary.summary_data.get("dish_frequency", [])
            preferred_food_ids = frozenset(
                r["food_item_id"] for r in dish_freq
                if r.get("times_selected", 0) >= 2
            )
            avoided_food_ids = frozenset(
                r["food_item_id"] for r in dish_freq
                if r.get("times_offered", 0) >= 3 and r.get("times_selected", 0) == 0
            )
        else:
            preferred_food_ids = frozenset()
            avoided_food_ids = frozenset()

        user_data["preferred_food_ids"] = preferred_food_ids
        user_data["avoided_food_ids"] = avoided_food_ids
        meal_plan = await meal_generator.generate_meal_plan(user_data, session)
```

### 1.4 BMI, BMR, TDEE formulas

All three live in `app/services/meal_generator/calculations.py`.

**BMI** — weight (kg) / height (m)²:

```python
# app/services/meal_generator/calculations.py:3-5
def calculate_bmi(height: float, weight: float) -> float:
    height_m = height / 100
    return weight / (height_m ** 2)
```

**BMR** — Mifflin-St Jeor equation (`10w + 6.25h − 5a`, +5 male / −161 female;
"Other"/unknown gender averages the two):

```python
# app/services/meal_generator/calculations.py:7-16
def calculate_bmr(gender: str, weight: float, height: float, age: int) -> float:
    if gender.lower() == 'male':
        return (10 * weight) + (6.25 * height) - (5 * age) + 5
    elif gender.lower() == 'female':
        return (10 * weight) + (6.25 * height) - (5 * age) - 161
    else:
        # "Other" / unknown gender — use average of male and female formulas
        male_bmr   = (10 * weight) + (6.25 * height) - (5 * age) + 5
        female_bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161
        return (male_bmr + female_bmr) / 2
```

**TDEE** — BMR × activity multiplier (defaults to sedentary 1.2 for unknown codes):

```python
# app/services/meal_generator/calculations.py:18-23
def calculate_tdee(bmr: float, activity_level: str) -> float:
    multipliers = {
        'S': 1.2, 'LA': 1.375,
        'MA': 1.55, 'VA': 1.725, 'SA': 1.9
    }
    return bmr * multipliers.get(activity_level, 1.2)
```

The activity codes map to enum values in `app/services/diet_plan_service.py:17-22`
(`SEDENTARY = "S"`, `LIGHTLY_ACTIVE = "LA"`, `MODERATELY_ACTIVE = "MA"`,
`VERY_ACTIVE = "VA"`, `SUPER_ACTIVE = "SA"`).

The generator computes all targets in `MealGenerator._calculate_targets()`:

```python
# app/services/meal_generator/meal_generator.py:124-135
        bmi = calculate_bmi(height, weight)
        bmr = calculate_bmr(gender, weight, height, age)
        tdee = calculate_tdee(bmr, activity_level)
        # health_sub_goal: first health goal (e.g. 'weight_loss', 'muscle_gain') used to
        # pick the correct macro split for Gym-Friendly and Diabetic-Friendly conditions.
        raw_goals = user_data.get("health_goals") or []
        health_sub_goal = raw_goals[0].lower().replace(" ", "_") if raw_goals else None
        # medical_conditions: passed through for PCOS / Thyroid macro overrides
        medical_conditions = user_data.get("medical_conditions") or []
        protein, carbs, fiber, fat = calculate_macronutrients(
            tdee, meal_plan_purchased, health_sub_goal, medical_conditions
        )
```

Macro splits (protein/carbs/fat as % of TDEE, ÷4 or ÷9 kcal per gram) vary by
`health_condition`, `health_sub_goal`, and medical-condition overrides
(PCOS > Hypothyroid > Hyperthyroid priority) — see
`calculate_macronutrients()` at `app/services/meal_generator/calculations.py:25-105`.
Default (Healthy): protein 20% / carbs 55% / fat 25%; fiber is `(tdee * 14) / 1000`
(line 104).

### 1.5 TDEE → Breakfast / Lunch / Dinner targets + buffer

The generator does **not** allocate 100% of TDEE to the three meals. Two 15% reductions
apply:

**Step 1** — 15% is held back up front (`effective_tdee`):

```python
# app/services/meal_generator/meal_generator.py:151-153
        targets = self._calculate_targets(user_data)

        effective_tdee = targets["tdee"] * 0.85
```

**Step 2** — the split fractions themselves sum to 0.85, not 1.0
(the remaining fraction is the unplanned buffer for snacks/beverages the
patient logs themselves):

```python
# app/services/meal_generator/meal_generator.py:32
DEFAULT_SPLIT = {"Breakfast": 0.25, "Lunch": 0.35, "Dinner": 0.25}
```

```python
# app/services/meal_generator/meal_generator.py:186-190
        meal_targets_calc = {
            "Breakfast": effective_tdee * split["Breakfast"],
            "Lunch":     effective_tdee * split["Lunch"],
            "Dinner":    effective_tdee * split["Dinner"],
        }
```

So for a TDEE of 2000 kcal: `effective_tdee = 1700`, Breakfast = 425, Lunch = 595,
Dinner = 425 (total planned = 1445 kcal = 72.25% of TDEE).

A doctor can override the split per patient via `PatientMealConfig.meal_split_override`
(integer percentages; the doctor PATCH endpoint validates they sum to 85 — see
`.claude/rules/backend-notes.md`, "meal-config endpoints"):

```python
# app/services/meal_generator/meal_generator.py:155-168
        split = DEFAULT_SPLIT
        patient_id = user_data.get("id")
        if patient_id:
            result = await session.execute(
                select(PatientMealConfig).where(PatientMealConfig.patient_id == int(patient_id))
            )
            config = result.scalar_one_or_none()
            if config and config.meal_split_override:
                o = config.meal_split_override
                split = {
                    "Breakfast": o["Breakfast"] / 100,
                    "Lunch":     o["Lunch"] / 100,
                    "Dinner":    o["Dinner"] / 100,
                }
```

---

## Section 2: Medical Condition Filtering

### 2.1 Condition strings → avoid/prefer tags

`app/services/meal_generator/tag_utils.py` is the canonical mapping from the exact
condition strings stored in `patients.medical_conditions` to tag strings present on
`food_items.avoid_tags` / `food_items.prefer_tags`:

```python
# app/services/meal_generator/tag_utils.py:7-23
CONDITION_AVOID_TAGS: dict[str, list[str]] = {
    "Type 2 Diabetes":  ["avoid_diabetes"],
    "Pre-diabetes":     ["avoid_diabetes"],
    "Hypertension":     ["avoid_hypertension"],
    "High Cholesterol": ["avoid_highchol"],
    "PCOS/PCOD":        ["avoid_pcos"],
    "Hypothyroidism":   ["avoid_hypothyroid"],
    "Hyperthyroidism":  ["avoid_hyperthyroid"],
    "Heart Disease":    ["avoid_heart"],
    "Kidney Disease":   ["avoid_kidney", "avoid_hypertension"],  # sodium restriction clinically indicated for CKD regardless of stage
    "Fatty Liver":      ["avoid_fattyliver"],
    "IBS/IBD":          ["avoid_ibs"],
    "Celiac Disease":   ["avoid_gluten"],
    "Gout":             ["avoid_gout"],
    "Osteoporosis":     [],
    "Anemia":           [],
}
```

```python
# app/services/meal_generator/tag_utils.py:25-41
CONDITION_PREFER_TAGS: dict[str, list[str]] = {
    "Type 2 Diabetes":  ["diabetes_friendly"],
    "Pre-diabetes":     ["diabetes_friendly"],
    "Hypertension":     ["heart_friendly"],
    "High Cholesterol": ["cholesterol_friendly"],
    "PCOS/PCOD":        ["pcos_friendly"],
    "Hypothyroidism":   ["thyroid_support"],
    "Hyperthyroidism":  [],
    "Heart Disease":    ["heart_friendly"],
    "Kidney Disease":   [],
    "Fatty Liver":      ["liver_friendly"],
    "IBS/IBD":          ["gut_friendly"],
    "Celiac Disease":   ["gluten_free"],
    "Gout":             [],
    "Osteoporosis":     ["calcium_rich"],
    "Anemia":           ["iron_rich"],
}
```

The dedup helpers (`tag_utils.py:52-73`) return a deduplicated union across all of a
patient's conditions. The generator converts the patient's conditions into frozensets
once per generation:

```python
# app/services/meal_generator/meal_generator.py:182-184
        _conditions = user_data.get("medical_conditions") or []
        patient_avoid_tags = frozenset(get_avoid_tags(_conditions))
        patient_prefer_tags = frozenset(get_prefer_tags(_conditions))
```

Note: `avoid_pcos` and `avoid_gout` currently match 0 food_items rows — silent no-ops
until Layer 2 ingredient tagging adds them (`tag_utils.py:5`).

### 2.2 The tag columns on `food_items`

```python
# app/models/db_models.py:37-38
    avoid_tags          = Column(JSONB, nullable=False, server_default='[]')
    prefer_tags         = Column(JSONB, nullable=False, server_default='[]')
```

### 2.3 Where the tags are applied

Filtering happens **inside the per-slot candidate query** (`base_stmt()` inside
`_pick_for_slot()`), not as a one-time pre-filter of the whole table. Avoid tags are a
hard `WHERE NOT` exclusion; prefer tags are a soft ranking boost.

**Avoid — hard exclusion.** Any food item carrying any of the patient's avoid tags is
removed from the candidate pool at every fallback level:

```python
# app/services/meal_generator/meal_generator.py:537-538
            if patient_avoid_tags:
                s = s.where(not_(or_(*[FoodItem.avoid_tags.contains([tag]) for tag in patient_avoid_tags])))
```

(`FoodItem.avoid_tags.contains([tag])` compiles to JSONB containment
`avoid_tags @> '["tag"]'::jsonb`, served by a GIN index — see
`.claude/rules/generator-notes.md`, "JSONB overlap for avoid filter".)

**Prefer — sort boost.** Items matching any prefer tag (or a doctor pin, or an R-7B
preferred ID) sort first in the candidate list:

```python
# app/services/meal_generator/meal_generator.py:513-517
        prefer_sort = or_(
            *[FoodItem.prefer_tags.contains([tag]) for tag in patient_prefer_tags],
            FoodItem.id.in_(pinned_food_ids),
            FoodItem.id.in_(preferred_food_ids) if preferred_food_ids else false(),
        ).desc()
```

```python
# app/services/meal_generator/meal_generator.py:539
            return s.order_by(prefer_sort, region_sort, cal_sort).limit(10)
```

**Other per-patient exclusions applied in the same query** (all hard `NOT IN` /
`WHERE` filters, `meal_generator.py:519-538`): doctor-blocked dishes
(`blocked_food_ids`), R-7B avoided dishes (`avoided_food_ids`), unverified dishes
(`FoodItem.is_verified == True`, line 524), and already-used dish IDs (Section 4).
Ingredient-level allergies are filtered in Python after the query
(`_is_allergenic`, `meal_generator.py:541-548`), built from `food_allergies` at
`meal_generator.py:241-250`.

---

## Section 3: Weekly Meal Plan Generation

### 3.1 Entry point and the 7-day × 3-meal loop

`MealGenerator.generate_meal_plan()` (`app/services/meal_generator/meal_generator.py:147-402`)
is the single generation routine. It iterates 7 days from `start_date`, and within each
day the three meal types:

```python
# app/services/meal_generator/meal_generator.py:198
        meal_types = ["Breakfast", "Lunch", "Dinner"]
```

```python
# app/services/meal_generator/meal_generator.py:252-257
        for day_offset in range(7):
            current_date = start_date + timedelta(days=day_offset)
            date_str = current_date.strftime("%Y-%m-%d")
            daily_used_ids.clear()   # new day → today's slate is clean

            for meal_type in meal_types:
```

### 3.2 Non-veg weekly budget (decides each slot's diet)

Before the loop, Non-Vegetarian patients get up to `min(nonveg_meals_per_week, 4)`
Lunch/Dinner slots pre-assigned as non-veg, max one per day; every other slot is
generated as Vegetarian:

```python
# app/services/meal_generator/meal_generator.py:225-238
        if diet_type == "Non-Vegetarian":
            nonveg_budget = min(int(user_data.get("nonveg_meals_per_week", 3)), 4)
            candidate_slots = [
                (d, mt) for d in range(7) for mt in ["Lunch", "Dinner"]
            ]
            random.shuffle(candidate_slots)
            days_taken: set = set()
            for d, mt in candidate_slots:
                if len(nonveg_assigned) >= nonveg_budget:
                    break
                if d in days_taken:      # no two non-veg meals on same day
                    continue
                nonveg_assigned.add((d, mt))
                days_taken.add(d)
```

```python
# app/services/meal_generator/meal_generator.py:265-269
                # ── Upgrade 1: per-slot diet type ────────────────────────
                if (day_offset, db_meal_time) in nonveg_assigned:
                    query_diet = "Non-Vegetarian"
                else:
                    query_diet = "Vegetarian"   # all non-assigned slots are veg
```

### 3.3 Slot templates (`meal_templates`)

The `meal_templates` table stores slot compositions as JSONB:

```python
# app/models/db_models.py:65-74
class MealTemplate(Base):
    __tablename__ = "meal_templates"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    meal_time   = Column(String(20), nullable=False)   # 'Breakfast','Lunch','Dinner','Morning_Snack','Evening_Snack'
    region      = Column(String(10), nullable=False)   # 'North','South','East','West'
    diet_type   = Column(String(30), nullable=False)
    plan_type   = Column(String(30), nullable=False)
    slots       = Column(JSONB, nullable=False)
    # slots format: [{"slot_type": "grain", "calorie_pct": 0.35, "required": true}, ...]
```

The generator looks up a template by (meal_time, region, diet_type, plan_type), with
two relaxation fallbacks — drop the region match, then try the Vegetarian template:

```python
# app/services/meal_generator/meal_generator.py:271-299
                # Fetch Template (use query_diet for template lookup)
                stmt = select(MealTemplate).where(
                    MealTemplate.meal_time == db_meal_time,
                    MealTemplate.region == region,
                    MealTemplate.diet_type == query_diet,
                    MealTemplate.plan_type == plan_type
                )
                result = await session.execute(stmt)
                template = result.scalars().first()

                if not template:
                    stmt_fallback = select(MealTemplate).where(
                        MealTemplate.meal_time == db_meal_time,
                        MealTemplate.diet_type == query_diet,
                        MealTemplate.plan_type == plan_type
                    )
                    result = await session.execute(stmt_fallback)
                    template = result.scalars().first()

                # If still no template for query_diet, try Vegetarian template
                if not template and query_diet != "Vegetarian":
                    stmt_veg = select(MealTemplate).where(
                        MealTemplate.meal_time == db_meal_time,
                        MealTemplate.region == region,
                        MealTemplate.diet_type == "Vegetarian",
                        MealTemplate.plan_type == plan_type
                    )
                    result = await session.execute(stmt_veg)
                    template = result.scalars().first()
```

**How `template.slots` is (and isn't) used:**

- **Breakfast**: `template.slots` is ignored — an in-code constant shadows it
  (beverage slot removed in Session 22E, its 10% redistributed):

  ```python
  # app/services/meal_generator/meal_generator.py:46-49
  BREAKFAST_SLOTS = [
      {"slot_type": "main_dish",     "calorie_pct": 0.78, "required": True},
      {"slot_type": "accompaniment", "calorie_pct": 0.22, "required": True},
  ]
  ```

- **Lunch/Dinner**: `template.slots` (grain / dal_protein / sabzi / accompaniment
  compositions, per the JSONB format comment above) IS the slot list used, unless the
  one-pot roll fires (next subsection):

  ```python
  # app/services/meal_generator/meal_generator.py:308-313
                  if db_meal_time == "Breakfast":
                      slot_lists = [BREAKFAST_SLOTS]   # Session 22E: shadows template.slots
                  else:
                      slot_lists = [template.slots]
                      if random.random() < ONE_POT_PROBABILITY:
                          slot_lists.insert(0, ONE_POT_SLOTS)
  ```

> **Code/comment discrepancy (documented as found, not fixed):** the module NOTE at
> `meal_generator.py:18-23` claims `meal_templates` "is NOT used in the live generation
> path" and mentions `LUNCH_SLOTS`/`DINNER_SLOTS` constants that do not exist in the
> file. As shown above, the table IS queried and `template.slots` IS the live slot list
> for Lunch/Dinner. Only the Breakfast rows are shadowed by a constant. Also,
> `_diet_fallback_chain()` (`meal_generator.py:440-452`) is defined but never called
> anywhere in `app/` — dead code.

### 3.4 The "One-pot" variant roll (40%)

For Lunch/Dinner, a per-slot-per-day 40% roll prepends a one-pot slot list (e.g. a
biryani/khichdi-style single dish + accompaniment). The standard template stays in
`slot_lists` as a fallback, so a thin one-pot pool can never drop the whole meal:

```python
# app/services/meal_generator/meal_generator.py:34-39
# ── Session 22B: one-pot meal variant (Lunch/Dinner only) ─────────────────────
ONE_POT_PROBABILITY = 0.40
ONE_POT_SLOTS = [
    {"slot_type": "one_pot",       "calorie_pct": 0.70, "required": True},
    {"slot_type": "accompaniment", "calorie_pct": 0.30, "required": True},
]
```

The `for slots in slot_lists:` loop (`meal_generator.py:319`) tries the one-pot list
first; if any required slot fails all fallback levels, `slot_failed` causes
`continue` to the standard template list (`meal_generator.py:352-353`), and `break`
at line 375 stops after the first slot list that succeeds.

### 3.5 Four combos per slot

Each (day, meal) slot produces **4 alternative combos** (84 rows/week = 7 days × 3
meals × 4), accumulated in `combo_slot_used_ids` so no dish repeats within one slot's
4 combos:

```python
# app/services/meal_generator/meal_generator.py:326-350
                    for combo_idx in range(4):
                        dishes, ok = await self._fill_slot_dishes(
                            session, slots, query_diet, region, db_meal_time, plan_type,
                            meal_target,
                            daily_used_ids, weekly_used_ids, combo_slot_used_ids,
                            ...
                        )
                        if not ok or (combo_idx == 0 and not dishes):
                            logger.warning(f"Required slot not found for {meal_type} combo {combo_idx}")
                            slot_failed = True
                            break

                        combo_slot_used_ids.update(d["food_id"] for d in dishes)
                        all_combos_for_slot.append(dishes)
                        if combo_idx == 0:
                            combo0_lookup = {d["slot_type"]: d for d in dishes}
```

Only combo-0's picks feed the daily/weekly variety memory and the ingredient
checklist (`meal_generator.py:355-364`). The combos are persisted to `weekly_combos`
by `DietPlanService.store_diet_plan()` as a single bulk insert
(`app/services/diet_plan_service.py:140-155`).

### 3.6 Picking a dish to fill a slot's calorie target

`_fill_slot_dishes()` computes each slot's calorie target from the meal target and the
slot's `calorie_pct`, then delegates to `_pick_for_slot()`:

```python
# app/services/meal_generator/meal_generator.py:625-631
        for slot in slots:
            slot_type = slot["slot_type"]
            required = slot.get("required", True)
            target_cal = meal_target * slot["calorie_pct"]

            food_item = await self._pick_for_slot(
                session, slot_type, chain_diet, region, meal_time, plan_type, target_cal,
```

Inside `_pick_for_slot()`, the candidate query constrains `cal_per_serving` to a
window around the target (a serving can be scaled ×0.5 to ×3.0, hence
`target/3 ≤ cal_per_serving ≤ target/0.5`), and ranks by prefer-boost, then
region match, then closeness to the calorie target, taking the top 10:

```python
# app/services/meal_generator/meal_generator.py:511-512
        region_sort = sa_case((FoodItem.region_tags.any(region), 0), else_=1)
        cal_sort = sa_func.abs(FoodItem.cal_per_serving - target_cal) if target_cal > 0 else FoodItem.id
```

```python
# app/services/meal_generator/meal_generator.py:519-539
        def base_stmt(try_diet: str, include_weekly: bool):
            s = select(FoodItem).where(
                FoodItem.slot_type == slot_type,
                FoodItem.diet_type == try_diet,
                FoodItem.meal_time_tags.any(meal_time),
                FoodItem.is_verified == True,  # noqa: E712 — Change 1: never serve unverified/test dishes
            )
            if target_cal > 0:
                s = s.where(FoodItem.cal_per_serving.between(target_cal / 3.0, target_cal / 0.5))
            ...
            return s.order_by(prefer_sort, region_sort, cal_sort).limit(10)
```

The first candidate that survives two Python-side checks wins: the slot-quality
blocklist (no chutneys/pickles/powders in protected slots) and the allergy check:

```python
# app/services/meal_generator/meal_generator.py:26-30
BLOCKLIST_PATTERNS = [
    "chutney", "powder", "masala powder", "pickle", "achar",
    "papad", "papadum", "murabba", "jam", "sauce", "dip",
]
PROTECTED_SLOTS = ["grain", "dal_protein", "main_dish", "sabzi", "one_pot"]
```

```python
# app/services/meal_generator/meal_generator.py:550-559
        def _pick(items: list) -> Optional[FoodItem]:
            for item in items:
                if slot_type in PROTECTED_SLOTS:
                    name_lower = item.recipe_name.lower()
                    if any(pat in name_lower for pat in BLOCKLIST_PATTERNS):
                        continue
                if _is_allergenic(item):
                    continue
                return item
            return None
```

The winning dish is portion-scaled to the slot's target, with the scaling factor
clamped to [0.5, 3.0]:

```python
# app/services/meal_generator/meal_generator.py:462-471
        cal_per_serving = float(food_item.cal_per_serving)
        factor = target_cal / cal_per_serving if cal_per_serving > 0 else 1.0
        factor = max(0.5, min(3.0, factor))
        return {
            "food_id":         food_item.id,
            "recipe_name":     food_item.recipe_name,
            "slot_type":       food_item.slot_type,
            "diet_type":       food_item.diet_type,
            "calories":        cal_per_serving,
            "scaled_calories": round(cal_per_serving * factor, 2),
```

Macros and per-dish ingredient grams scale by the same factor
(`meal_generator.py:472-477` and `_build_dish_ingredients()` at 404-427; pantry
staples skipped).

---

## Section 4: Variety & Repeat Logic

### 4.1 The three memory sets

```python
# app/services/meal_generator/meal_generator.py:216-219
        daily_used_ids  = set()   # HARD block — cleared every day, no same dish twice per day
        prior_seed      = frozenset(user_data.get("prior_used_food_ids") or [])
        weekly_used_ids = set(prior_seed)
        # Acts as SOFT preference — dropped at Level 2 if pool is exhausted.
```

- `daily_used_ids` — hard block, cleared at the start of each day
  (`daily_used_ids.clear()`, `meal_generator.py:255`).
- `weekly_used_ids` — soft variety memory across the whole week.
- `combo_slot_used_ids` — hard block within one slot's 4 combos
  (`meal_generator.py:321`, updated at 347).

Only combo-0's dishes are folded into the daily/weekly memory once a slot completes:

```python
# app/services/meal_generator/meal_generator.py:355-356
                    weekly_used_ids.update(d["food_id"] for d in all_combos_for_slot[0])
                    daily_used_ids.update(d["food_id"] for d in all_combos_for_slot[0])
```

And only the IDs picked *this* generation are returned/persisted — never the seed —
to prevent exclusion-set snowballing across regenerations:

```python
# app/services/meal_generator/meal_generator.py:398-402
            "used_food_ids": list(weekly_used_ids - prior_seed),
            # Only IDs picked THIS generation — never the seed. Persisting the
            # accumulated union snowballs the exclusion set across regenerations
            # until the candidate pool is exhausted and variety collapses.
```

(Cross-week seeding of `prior_used_food_ids` was removed in Session 22A — see
`app/services/diet_plan_service.py:49-51` — so in the current call path the seed is
empty and `weekly_used_ids` covers within-week variety only.)

### 4.2 How the memories enter the query

`daily_used_ids` and `combo_slot_used_ids` are always excluded; `weekly_used_ids` is
excluded only when `include_weekly=True`:

```python
# app/services/meal_generator/meal_generator.py:528-532
            excluded = set(daily_used_ids) | set(combo_slot_used_ids)
            if include_weekly:
                excluded |= set(weekly_used_ids)
            if excluded:
                s = s.where(FoodItem.id.notin_(excluded))
```

### 4.3 Levels 1–3: the pool-fallback cascade

The diet-type pools driving the cascade:

```python
# app/services/meal_generator/meal_generator.py:57-69
DIET_TYPE_HIERARCHY = {
    "Vegetarian":     ["Vegetarian"],
    "Non-Vegetarian": ["Non-Vegetarian", "Eggetarian"],
    "Eggetarian":     ["Eggetarian", "Vegetarian"],
}
# DIET_TYPE_FALLBACK: NEW Level 3 — tried only after the primary pool
# (Levels 1-2) is fully exhausted. Vegetarian is always reachable since
# Vegetarian itself has no further fallback (empty list).
DIET_TYPE_FALLBACK = {
    "Non-Vegetarian": ["Vegetarian"],
    "Eggetarian":     ["Vegetarian"],
    "Vegetarian":     [],
}
```

The cascade itself — **Level 2 is exactly where the weekly variety memory is dropped**
(`include_weekly=False`), i.e. repeating a dish from earlier in the week is preferred
over failing the slot:

```python
# app/services/meal_generator/meal_generator.py:564-581
        primary_chain = DIET_TYPE_HIERARCHY.get(diet_type, [diet_type])

        # Level 1 — primary pool, weekly memory excluded (soft variety preference)
        for try_diet in primary_chain:
            if (picked := _pick(await fetch(base_stmt(try_diet, include_weekly=True)))) is not None:
                return picked

        # Level 2 — primary pool, weekly memory dropped (weekly exclusion exhausted)
        for try_diet in primary_chain:
            if (picked := _pick(await fetch(base_stmt(try_diet, include_weekly=False)))) is not None:
                return picked

        # Level 3 (NEW) — fallback diet types (e.g. Vegetarian for Non-Veg/Eggetarian)
        for try_diet in DIET_TYPE_FALLBACK.get(diet_type, []):
            if (picked := _pick(await fetch(base_stmt(try_diet, include_weekly=False)))) is not None:
                return picked

        return None
```

Summary of the cascade for one slot pick:

| Level | Diet pool | Weekly memory | Daily / combo blocks |
|---|---|---|---|
| 1 | `DIET_TYPE_HIERARCHY[diet]` | excluded (variety enforced) | always excluded |
| 2 | `DIET_TYPE_HIERARCHY[diet]` | **dropped** | always excluded |
| 3 | `DIET_TYPE_FALLBACK[diet]` | dropped | always excluded |
| 4 | (no query) | — | reuse combo-0's dish |

Hard filters (avoid tags, blocked/avoided IDs, allergies, `is_verified`, blocklist
patterns) are never dropped at any level.

### 4.4 Level 4: combo-0 duplication (last resort)

If Levels 1–3 all return nothing for a combo beyond the first, the slot reuses
combo-0's dish for that slot_type instead of failing the whole slot:

```python
# app/services/meal_generator/meal_generator.py:646-662
            # Level 4 — pool exhausted at every diet level; duplicate combo-0's
            # pick for this slot_type rather than dropping the slot.
            if combo0_lookup and slot_type in combo0_lookup:
                logger.warning(
                    f"Pool exhausted for slot_type={slot_type} diet={chain_diet} "
                    f"combo_idx={combo_idx} — reusing combo-0 dish "
                    f"food_id={combo0_lookup[slot_type]['food_id']}"
                )
                dishes.append(dict(combo0_lookup[slot_type]))
                continue

            if required:
                logger.warning(
                    f"Required slot_type={slot_type} not found (diet={chain_diet}, "
                    f"combo_idx={combo_idx}) — no Level-4 fallback available (combo-0 itself)"
                )
                return dishes, False
```

`ok=False` from a required slot propagates up: the caller abandons that slot list
(e.g. one-pot → standard template fallback, `meal_generator.py:352-353`); if the
standard template also fails, that (day, meal) slot is skipped entirely. The route
handler validates the final plan structure and retries generation up to 3 times
(`_validate_generated_plan` + `MAX_ATTEMPTS = 3` loop,
`app/routers/diet_plans.py:177-249`), returning HTTP 503 rather than 500 if all
attempts fail.
