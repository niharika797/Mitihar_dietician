# Backend Deep Functional Audit Report

### 1. Meal Recommendation Algorithm — How does it actually work?
*File: [app/services/meal_generator/meal_generator.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/services/meal_generator/meal_generator.py)*

- **Inputs**: It accepts a `user_data` dictionary and derives a [MealPlanTargets](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/services/meal_generator/meal_generator.py#16-38) context object (`ctx`). The `user_data` contains: `height`, [weight](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/services/progress_service.py#57-67), `age`, `gender`, `activity_level`, `meal_plan_purchased`, `health_condition`, `region`, [diet](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/routers/diet_plans.py#205-225) and operational fields like `tolerance` and `carb_tolerance`.
- **Logic to select meals**: 
  1. Filters the dataset primarily by the user's `DIET` (strict matching for "Vegetarian", substring matching for "Non-Vegetarian" and "Eggetarian").
  2. Applies `Region` filtering on top of diet filtering.
  3. Excludes meals already present in `ctx.meal_history[meal_type]` for the current generation run.
  4. Shuffles the remaining pool via `.sample(frac=1)`.
  5. Cycles through 7 days, looking for an "Option 1" and "Option 2" for each meal (Breakfast, Lunch, Dinner).
  6. The core selection logic ([_find_suitable_meal](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/services/meal_generator/meal_generator.py#520-558)) iterates through candidates, evaluating a scaling `factor` (bounded between 0.5x and 2.0x) to proportionally match the candidate's base calories/protein to `target_calories` / `target_protein`.
  7. Checks [_meets_nutritional_requirements](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/services/meal_generator/meal_generator.py#422-431): candidate's scaled macros must map to the targets within an accepted `tolerance` and `carb_tolerance` range. 
  8. If it fails, it cascades through fallbacks: relaxing region filters -> relaxing tolerances -> wiping history cache -> forcing the closest available meal.
- **Output**: Returns a dictionary: `{"meals": organized_meals, "ingredient_checklist": checklist_records}`. The `organized_meals` is a flat list of dictionaries, each containing: `Date`, `Meal Type`, `Option` (e.g. Option 1), `Menu Names`, `Diet Type`, `Region`, macros (`Total Calories`, etc.), `Ingredients Scaling` (dict of ingredient to gram amounts), and `Sr. No.`.
- **Vegetarian/Non-Vegetarian Split**: Managed through [_normalize_diet_label](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/services/meal_generator/meal_generator.py#53-75) and pandas dataframe substring filtering. If `user_diet == "vegetarian"`, it drops everything not explicitly "vegetarian". If "non-vegetarian", it strictly selects rows where `DIET` contains "non". If options exhaust, history resets, but it stays within the diet lane.
- **Personalization**: There is no historical memory of past plans or allergy filters. The personalization relies exclusively on user macros and immediate history clearing of the *current* generation run to avoid direct duplicate IDs on consecutive days.
- **7-day plan structure**: The days are not nested. The loop creates a flat sequence of dictionaries marked by a calculated `Date` string (e.g. `2026-02-25`) derived from `start_date` plus a `timedelta` of 0 to 6 days in a flat loop. 

### 2. Progress Tracking — What is actually being stored?
*Files: [app/routers/progress.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/routers/progress.py), [app/services/progress_service.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/services/progress_service.py)*

- **Stored Data Fields**: The MongoDB collection `progress` stores flat log entries across various types as `user_id`, `type`, `data` (dict), and `timestamp`. 
  - [meal](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/routers/progress.py#13-22): `data` contains the full `MealLogCreate` pydantic model dump (e.g. calories, meal items).
  - [water](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/routers/progress.py#23-32): `data: {"glasses": glasses}`
  - [steps](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/routers/progress.py#33-42): `data: {"steps": steps}`
  - [weight](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/services/progress_service.py#57-67): `data: {"weight": weight}`
  - [activity](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/routers/progress.py#55-64): `data` contains the full `ActivityLogCreate` dump.
- **Aggregation logic**: `GET /api/v1/progress/weekly` computes total calories for meals over the last 7 days and outputs `average_calories_consumed` (`total_cals / 7`). `GET /today` sums today's calories, water glasses, and steps.
- **Updates/Deletes**: Iterating both files shows absolutely **no** `PUT` or `DELETE` endpoints for logs. A patient cannot update or delete a log entry. 
- **Comparison logic**: The `/today` endpoint yields a `remaining` block (`target - total_calories`), but the target is hardcoded as `2000` (e.g., `"target": 2000 # Should come from diet plan`). There is no actual programmatic logic comparing logged calories against the user's specific diet plan targets.

### 3. User Onboarding — What does the current flow capture?
*Files: [app/routers/auth.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/routers/auth.py), [app/schemas/user.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/schemas/user.py)*

- **Current fields collected**: Handled via [UserCreate](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/schemas/user.py#51-53) schema on `POST /register`: `email`, `password`, `name`, `age`, `gender`, `height`, [weight](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/services/progress_service.py#57-67), `activity_level`, [diet](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/routers/diet_plans.py#205-225), `health_condition`, [diabetes_status](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/schemas/user.py#36-43) (optional), [gym_goal](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/schemas/user.py#43-50) (optional), and `region` (optional).
- **Validation**: 
  - Age, Height, Weight must strictly be `> 0`. 
  - Enum-enforced `activity_level` (S, LA, MA, VA, SA), [diet](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/routers/diet_plans.py#205-225) (Vegetarian, Non-Vegetarian), and `health_condition` (Healthy, Diabetic-Friendly, Gym-Friendly).
  - Cross-field validation via `@field_validator`: If `health_condition == HealthCondition.DIABETIC`, [diabetes_status](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/schemas/user.py#36-43) must be `controlled` or `uncontrolled`. If `health_condition == HealthCondition.GYM`, [gym_goal](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/schemas/user.py#43-50) must be `weight_loss`, `muscle_gain`, or `maintenance`.
  - There is no automatic BMI calculation trigger in the validation phase itself.
- **Onboarding Flow**: There is no multi-step onboarding flow. All preferences, dietary restrictions, and physical parameters are captured synchronously during the initial `POST /register` call. 
- **First meal plan generation**: Manual. Registration stores the user in MongoDB. To get a plan, the client must subsequently call `POST /generate` themselves.

### 4. Calculations — How are BMI, BMR, TDEE computed?
*Files: [app/routers/calculations.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/routers/calculations.py), [app/services/meal_generator/calculations.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/services/meal_generator/calculations.py)*

- **BMI**: `weight / ((height / 100) ** 2)`. Inputs are Weight in kg, Height in cm.
- **BMR**: Uses the **Mifflin-St Jeor** equation heavily: 
  - Male: [(10 * weight) + (6.25 * height) - (5 * age) + 5](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/main.py#40-43)
  - Female: [(10 * weight) + (6.25 * height) - (5 * age) - 161](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/main.py#40-43)
- **TDEE**: Computed by multiplying BMR with the chosen activity multiplier (`bmr * multiplier`).
- **Are they stored?**: No. They are fetched repeatedly on-the-fly (`/bmr`, `/tdee`, `/bmi` endpoints read direct inputs from `current_user` and calculate the output dynamically). They are not stored in the DB.
- **Activity level options**: 
  - Sedentary (`S`): 1.2
  - Lightly Active (`LA`): 1.375
  - Moderately Active (`MA`): 1.55
  - Very Active (`VA`): 1.725
  - Super Active (`SA`): 1.9

### 5. Diet Plan Storage — How is the generated plan stored?
*Files: [app/routers/diet_plans.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/routers/diet_plans.py), [app/models/diet_plan.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/models/diet_plan.py)*

- **Document Structure**: Stored in the MongoDB `diet_plans` collection matching the [DietPlan](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/models/diet_plan.py#25-31) class. Contains `user_id`, `created_at` (timestamp), [meals](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/routers/diet_plans.py#78-104) (a `List[Dict]` holding the full JSON arrays of generated meals), and [ingredient_checklist](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/services/meal_generator/meal_generator.py#563-605) (a `List[Dict]` of grocery items). 
- **Meal Embedded or Reference?**: Each meal is stored with its *full data* nested inside the document (`Date`, `Menu Names`, `Total Calories`, `Ingredients Scaling` mapping). It is not a reference ID to a database of meals.
- **Regeneration**: `POST /generate` checks if an `existing_plan` exists. If so, it outright rejects with an `HTTP 400 "Diet plan already exists for this user"`. To regenerate, a user must call `DELETE /delete` mapping and request generation again, or interact with an `/update` method on the frontend. 
- **Versioning**: There is completely zero versioning or history. Calling `/update` or `/adjust` strictly overrides the MongoDB JSON. 
- **Ingredient Checklist Creation**: Constructed dynamically via [generate_ingredient_checklist()](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/services/meal_generator/meal_generator.py#563-605) directly from the meal plan list. It sweeps each assigned meal, unpacks the `Ingredients Scaling` dict, aggregates gram totals by dict key (the string name of the ingredient), and inserts them into a pandas dataframe which renders out sorted by weight descending.

### 6. Notifications — Does anything exist?
- **Global Search**: After conducting a precise Regex search targeting [(notification|push|firebase|fcm|email|smtp|sendgrid|celery|background|scheduler|cron)](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/main.py#40-43), the results turned up completely empty. 
- The ONLY usage of the word "email" is as the literal registration `email` field inside [UserBase](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/schemas/user.py#21-50) schema. There are absolutely no SMTP servers, no Celery queues, no cron jobs, and no push notification adapters linked anywhere inside the application. 

### 7. Rate Limiting — What endpoints are currently protected?
*Files: [app/main.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/main.py), [app/routers/auth.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/routers/auth.py), [app/routers/diet_plans.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/routers/diet_plans.py), [app/routers/meal_plan.py](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/app/routers/meal_plan.py)*

- **Backend Logic**: Instantiates an in-memory `slowapi.Limiter(key_func=get_remote_address)`. The commented lines indicate a Redis deployment is scoped, but the current backend is pure memory routing.
- **Protected Endpoints**:
  1. `POST /api/v1/auth/token`: `@limiter.limit("20/minute")`
  2. `POST /api/v1/diet-plans/generate`: `@limiter.limit("10/hour")`
  3. `POST /api/v1/meal-plan/adjust`: `@limiter.limit("10/hour")`

---

### 8. File / Folder Structure — Full tree

> [!NOTE]
> *The resulting file tree is massive (over 17,000 lines).* To prevent the UI editor from crashing or freezing, the 800+ KB full directory tree has been saved directly to your workspace. 
> 
> You can safely view the full un-truncated tree in your project root at:
> [c:\Users\Lenovo\Desktop\Code\2026\Nutria\Mitihar_dietician\tree_utf8_v2.txt](file:///c:/Users/Lenovo/Desktop/Code/2026/Nutria/Mitihar_dietician/tree_utf8_v2.txt)
