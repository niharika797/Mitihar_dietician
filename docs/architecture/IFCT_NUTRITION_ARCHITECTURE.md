# IFCT 2017 Nutrition Architecture

How IFCT 2017 (Indian Food Composition Tables) nutritional data is stored, mapped, and used to calculate recipe and meal plan nutrition in this codebase. Every claim below cites a file, line number, and code snippet, verified as of 2026-07-15.

**Key architectural fact up front:** the bottom-up calculation (ingredient quantity × per-100g nutrition) exists **only as an offline batch script** (`scripts/recalculate_recipe_nutrition.py`). It is **not** part of the runtime application. The FastAPI app (`app/`) never touches the `recipe_ingredients` or `ingredients` tables at request time — it reads the pre-computed `food_items.*_per_serving` columns and scales them. `RecipeIngredient`/`Ingredient` appear in `app/` only as ORM model definitions (`app/models/db_models.py:824-883`); a grep for `recipe_ingredients` across `app/` returns matches in `db_models.py` only.

---

## Section 1: Storage of Raw Ingredient Nutrition (The IFCT Data)

### 1.1 The `ingredients` table

Raw per-100g nutrition for base ingredients (Rice, Wheat, Curd, …) lives in the `ingredients` table. Model: `app/models/db_models.py:824-858`.

```python
class Ingredient(Base):
    __tablename__ = "ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    name_hindi: Mapped[str | None] = mapped_column(Text, nullable=True)
    name_normalized: Mapped[str | None] = mapped_column(Text, nullable=True)
    calories_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    protein_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    carbs_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fat_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    fiber_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    sodium_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    iron_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    calcium_per_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit_weight_g: Mapped[Decimal | None] = mapped_column(Numeric, nullable=True)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ...
    __table_args__ = (
        UniqueConstraint("name", "source", name="uq_ingredient_name_source"),
        ...
    )
```

All nutrition columns are nullable `Float` per 100 g. The `source` column records provenance; the values written by the seeding pipeline are:

| `source` value | Written by | Meaning |
|---|---|---|
| `'pending'` | `scripts/seed_ingredients_names.py:41-45` | Name seeded, nutrition NULL |
| `'estimated_llm'` | `scripts/seed_ingredient_nutrition.py:121` | Local LLM (Gemma via llama-server) estimate |
| `'IFCT2017'` | `scripts/import_ifct.py:260` | Matched against IFCT 2017 PDF Table 1 |

There is **no** JSON/Python file holding IFCT data, and nutrition is **not** embedded in `recipe_ingredients` (that table stores only quantities — see Section 2). The IFCT source of truth is the PDF itself, parsed at import time.

### 1.2 How the data got there (seeding pipeline, in order)

**Step 1 — names.** `scripts/seed_ingredients_names.py` extracts distinct ingredient names out of the `food_items.ingredients` JSONB column and inserts them with NULL nutrition (`scripts/seed_ingredients_names.py:26-45`):

```python
result = await db.execute(text("""
    SELECT DISTINCT ing->>'name' AS name
    FROM food_items, jsonb_array_elements(ingredients) AS ing
    ...
"""))
...
INSERT INTO ingredients (name, name_normalized, source, is_verified)
VALUES (:name, :norm, 'pending', false)
```

**Step 2 — LLM baseline nutrition.** `scripts/seed_ingredient_nutrition.py` batches 20 NULL-nutrition ingredients per call to a local llama-server (`LLAMA_URL = "http://localhost:11434/v1/chat/completions"`, line 23) and writes per-100g estimates with `source = 'estimated_llm'` (`scripts/seed_ingredient_nutrition.py:114-122`):

```python
await db.execute(text("""
    UPDATE ingredients SET
        calories_per_100g = :cal,
        protein_per_100g  = :pro,
        carbs_per_100g    = :carb,
        fat_per_100g      = :fat,
        fiber_per_100g    = :fib,
        source            = 'estimated_llm'
    WHERE id = :id
"""), ...)
```

**Step 3 — IFCT 2017 upgrade.** `scripts/import_ifct.py` parses Table 1 (Proximate Principles) directly out of the PDF at `C:\Users\Lenovo\Desktop\Code\2026\Nutria\Mitihar_dietician\IFCT2017.pdf` (`scripts/import_ifct.py:18`) using `pdfplumber`, converts energy kJ → kcal (`kcal = ekj / 4.184`, line 62), matches rows against `ingredients` via a 3-pass strategy (exact normalized name → primary comma-segment → ≥2 significant-token overlap, lines 149-178), applies a blocklist of 4 known-wrong matches plus a kcal < 10 floor (lines 214-227), and — only with `--write` and match rate ≥ 30% — overwrites the matched ingredients (`scripts/import_ifct.py:253-264`):

```python
conn.execute(text("""
    UPDATE ingredients
    SET calories_per_100g = :kcal,
        protein_per_100g  = :pro,
        fat_per_100g      = :fat,
        carbs_per_100g    = :carb,
        fiber_per_100g    = :fib,
        source            = 'IFCT2017',
        is_verified       = true
    WHERE id = :id
"""), ...)
```

So IFCT values overwrite LLM estimates for the subset of ingredients that match; the rest stay `'estimated_llm'`. The script's final printout points at the propagation step (`scripts/import_ifct.py:267`): *"Next: re-run scripts/recalculate_recipe_nutrition.py to propagate to food_items."*

### 1.3 A second, separate nutrition path: `food_items.ingredients` JSONB

Independent of the ingredient-chain above, each dish also carries a denormalized ingredient list as JSONB on `food_items` itself (`app/models/db_models.py:32`):

```python
ingredients         = Column(JSONB, nullable=False, default=[])  # [{"name": str, "amount_g": float}]
```

This JSONB holds names + gram amounts only — **no nutrition values**. It predates the `ingredients`/`recipe_ingredients` tables (it is the source they were seeded from, per Step 1 above) and is what the runtime meal generator reads (Section 4.2).

Historical note: the original bulk seed of `food_items` (`scripts/seed_6k_recipes.py`) computed per-serving macros at seed time from **USDA** lookups, not IFCT (`scripts/seed_6k_recipes.py:225-229`):

```python
nutrition = usda_lookup(name)
if nutrition:
    factor = grams / 100.0
    for key in totals:
        totals[key] += nutrition[key] * factor
```

…and divided by servings (`scripts/seed_6k_recipes.py:241`): `"cal_per_serving": round(totals["cal"] / servings, 2)`. Those USDA-derived values were later overwritten for eligible recipes by the IFCT-chain recalculation (Section 3).

---

## Section 2: The Recipe-to-Ingredient Mapping

### 2.1 The `recipe_ingredients` table

Model: `app/models/db_models.py:865-883`.

```python
class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    food_item_id: Mapped[int] = mapped_column(Integer, ForeignKey("food_items.id",  ondelete="CASCADE"),  nullable=False)
    ingredient_id: Mapped[int] = mapped_column(Integer, ForeignKey("ingredients.id", ondelete="RESTRICT"), nullable=False)
    quantity_g: Mapped[float] = mapped_column(Float, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("food_item_id", "ingredient_id", name="uq_recipe_ingredient"),
        Index("idx_ri_food_item",  "food_item_id"),
        Index("idx_ri_ingredient", "ingredient_id"),
    )
```

- **Link:** `food_item_id` → `food_items.id` (dish; CASCADE delete), `ingredient_id` → `ingredients.id` (raw ingredient; RESTRICT delete).
- **Quantity column:** `quantity_g`, Python type `float` / SQL `Float`, NOT NULL. One row per (dish, ingredient) — enforced by `uq_recipe_ingredient`.

### 2.2 How the mapping was populated

`scripts/seed_recipe_ingredients.py` walks every `food_items` row with non-empty JSONB ingredients, normalizes each name (lowercase, collapsed whitespace — `scripts/seed_recipe_ingredients.py:20-21`), looks it up in `ingredients.name_normalized`, and inserts (`scripts/seed_recipe_ingredients.py:72-75`):

```python
await db.execute(text("""
    INSERT INTO recipe_ingredients (food_item_id, ingredient_id, quantity_g)
    VALUES (:fid, :iid, :qty)
"""), {"fid": food_id, "iid": ing_id, "qty": float(amount_g)})
```

Idempotent: it DELETEs a dish's existing rows before re-inserting (`scripts/seed_recipe_ingredients.py:52-54`). Names that don't match an `ingredients` row are skipped and reported — so a dish's `recipe_ingredients` rows can be a **subset** of its JSONB list. This is why the recalculation script uses a coverage threshold (Section 3).

---

## Section 3: The "Bottom-Up" Calculation Logic

### 3.1 Where it lives — and where it does NOT

The bottom-up math **exists**, in exactly one place: `scripts/recalculate_recipe_nutrition.py`. It is a manually-run offline batch script (sync SQLAlchemy, raw SQL). **There is no runtime service, endpoint, or ORM event in `app/` that recomputes dish nutrition from ingredients.** If an ingredient's IFCT value changes, `food_items` stays stale until someone re-runs this script (which is exactly what `scripts/import_ifct.py:267` instructs).

### 3.2 The math

For every `food_items` row, the script joins its `recipe_ingredients` to `ingredients` (`scripts/recalculate_recipe_nutrition.py:38-49`):

```sql
SELECT
    ing.calories_per_100g,
    ing.protein_per_100g,
    ing.carbs_per_100g,
    ing.fat_per_100g,
    ing.fiber_per_100g,
    ri.quantity_g
FROM recipe_ingredients ri
JOIN ingredients ing ON ing.id = ri.ingredient_id
WHERE ri.food_item_id = :fid
```

Coverage gate (`scripts/recalculate_recipe_nutrition.py:21,61-70`): an ingredient counts as "covered" if calories, protein, carbs, and fat are all non-NULL; the recipe is recalculated only if `coverage >= 0.80` (`COVERAGE_THRESHOLD = 0.80`).

The actual `(quantity_g / 100) × per_100g` computation (`scripts/recalculate_recipe_nutrition.py:71-75`):

```python
cal = sum((r[0] or 0) * r[5] / 100 for r in rows)
pro = sum((r[1] or 0) * r[5] / 100 for r in rows)
crb = sum((r[2] or 0) * r[5] / 100 for r in rows)
fat = sum((r[3] or 0) * r[5] / 100 for r in rows)
fib = sum((r[4] or 0) * r[5] / 100 for r in rows)
```

(`r[5]` = `ri.quantity_g`; `r[0..4]` = the per-100g columns.)

Note: the sum over all ingredient rows becomes the per-serving value directly — there is **no division by a servings count** here (unlike the original USDA seed, Section 1.3). The recipe's `quantity_g` rows are implicitly treated as one serving.

### 3.3 Where the result is saved

Directly onto `food_items`, including `cal_per_serving`, with provenance recorded in `nutrition_source` (`scripts/recalculate_recipe_nutrition.py:76-86`):

```python
session.execute(text("""
    UPDATE food_items
    SET cal_per_serving     = :cal,
        protein_per_serving = :pro,
        carbs_per_serving   = :crb,
        fat_per_serving     = :fat,
        fiber_per_serving   = :fib,
        nutrition_source    = 'calculated'
    WHERE id = :fid
"""), ...)
```

Recipes below the coverage threshold, or with zero `recipe_ingredients` rows, keep their existing macros and get `nutrition_source = 'manual'` (`scripts/recalculate_recipe_nutrition.py:51-59, 88-92`). The `nutrition_source` column is declared at `app/models/db_models.py:34`:

```python
nutrition_source    = Column(Text, nullable=False, server_default="manual")
```

The target columns on `FoodItem` (`app/models/db_models.py:22-26`):

```python
cal_per_serving     = Column(Numeric(7, 2), nullable=False)
protein_per_serving = Column(Numeric(6, 2), nullable=False, default=0)
carbs_per_serving   = Column(Numeric(6, 2), nullable=False, default=0)
fat_per_serving     = Column(Numeric(6, 2), nullable=False, default=0)
fiber_per_serving   = Column(Numeric(6, 2), nullable=False, default=0)
```

---

## Section 4: Patient Meal Scaling

All runtime scaling happens in `app/services/meal_generator/meal_generator.py`, operating exclusively on the pre-computed `food_items.*_per_serving` columns. The IFCT chain is never queried at request time.

### 4.1 Candidate pre-filter: only dishes scalable into the target

When selecting candidate dishes for a slot, the pool query keeps only dishes whose `cal_per_serving` can reach the slot's calorie target within the 0.5×–3.0× clamp (`app/services/meal_generator/meal_generator.py:526-527`):

```python
if target_cal > 0:
    s = s.where(FoodItem.cal_per_serving.between(target_cal / 3.0, target_cal / 0.5))
```

(A dish needing factor > 3.0 or < 0.5 to hit `target_cal` is excluded up front.)

### 4.2 The scaling factor: `_assemble_dish`

`app/services/meal_generator/meal_generator.py:454-478`:

```python
@staticmethod
def _assemble_dish(food_item: FoodItem, target_cal: float) -> dict:
    ...
    cal_per_serving = float(food_item.cal_per_serving)
    factor = target_cal / cal_per_serving if cal_per_serving > 0 else 1.0
    factor = max(0.5, min(3.0, factor))
    return {
        "food_id":         food_item.id,
        ...
        "calories":        cal_per_serving,
        "scaled_calories": round(cal_per_serving * factor, 2),
        "factor":          round(factor, 3),
        "protein":         round(float(food_item.protein_per_serving) * factor, 2),
        "carbs":           round(float(food_item.carbs_per_serving) * factor, 2),
        "fat":             round(float(food_item.fat_per_serving) * factor, 2),
        "fiber":           round(float(food_item.fiber_per_serving) * factor, 2) if food_item.fiber_per_serving else 0.0,
        "ingredients":     MealGenerator._build_dish_ingredients(food_item, factor),
    }
```

`factor = target_cal / cal_per_serving`, clamped to `[0.5, 3.0]` (line 463-464). Every macro is multiplied by the same factor (linear portion scaling).

### 4.3 Ingredient quantity scaling for display / shopping list

**Important:** the scaled ingredient list shown to the patient comes from the **JSONB** `food_items.ingredients` column, **not** from `recipe_ingredients`. `_build_dish_ingredients` (`app/services/meal_generator/meal_generator.py:404-427`):

```python
@staticmethod
def _build_dish_ingredients(food_item: FoodItem, factor: float) -> list:
    """Per-dish ingredient list with portion-scaled gram amounts (pantry staples skipped)."""
    dish_ingredients: list = []
    ...
    for _ing in (food_item.ingredients or []):
        ...
        if _ing.get("is_pantry_staple"):
            continue
        ...
        _raw = _ing.get("amount_g") or _ing.get("quantity") or 0
        ...
        _amt = round(float(_raw) * factor, 1)
        ...
        if _amt > 0:
            dish_ingredients.append({"name": _name, "amount_g": _amt})
    return dish_ingredients
```

Each dish's JSONB `amount_g` is multiplied by the same portion `factor` (line 419).

Per-meal aggregation into "Ingredients Scaling" (combo 0 only) — `app/services/meal_generator/meal_generator.py:358-364`:

```python
ingredients_scaling: dict = {}
for dish in all_combos_for_slot[0]:
    for ing in dish["ingredients"]:
        ingredients_scaling[ing["name"]] = round(
            ingredients_scaling.get(ing["name"], 0) + ing["amount_g"], 2
        )
combo0_ingredient_sources.append({"Ingredients Scaling": ingredients_scaling})
```

Weekly shopping checklist sums those per-meal maps across the plan — `generate_ingredient_checklist`, `app/services/meal_generator/meal_generator.py:667-692`:

```python
def generate_ingredient_checklist(self, meals):
    all_ingredients = {}
    for meal in meals:
        ingredients_scaled = meal.get("Ingredients Scaling", {})
        for ingredient, amount in ingredients_scaled.items():
            normalized = ingredient.strip().title()
            if normalized in all_ingredients:
                all_ingredients[normalized] += amount
            else:
                all_ingredients[normalized] = amount
    ...
    ingredients_df = pd.DataFrame([
        {"Ingredient": k, "Total Amount (g)": round(v, 2)}
        for k, v in all_ingredients.items()
    ])
    ...
    return ingredients_df.sort_values("Total Amount (g)", ascending=False)
```

---

## Summary: The Full Data Flow

```
IFCT2017.pdf (repo root)
    │  pdfplumber Table-1 extraction + 3-pass name match     [scripts/import_ifct.py]
    ▼
ingredients (calories_per_100g … fiber_per_100g, source='IFCT2017' | 'estimated_llm')
    │                                                        [app/models/db_models.py:824-858]
    │  JOIN via recipe_ingredients (food_item_id, ingredient_id, quantity_g)
    │                                                        [app/models/db_models.py:865-883]
    ▼
OFFLINE:  sum(per_100g × quantity_g / 100), coverage ≥ 0.80  [scripts/recalculate_recipe_nutrition.py:71-75]
    │  UPDATE food_items SET *_per_serving, nutrition_source='calculated'   [:76-86]
    ▼
food_items.cal_per_serving (+ macros)                        [app/models/db_models.py:22-26]
    │
    │  RUNTIME (meal generator — never touches ingredients/recipe_ingredients):
    │    pool filter: cal_per_serving BETWEEN target/3.0 AND target/0.5    [meal_generator.py:527]
    │    factor = clamp(target_cal / cal_per_serving, 0.5, 3.0)            [meal_generator.py:463-464]
    │    macros × factor                                                    [meal_generator.py:471-476]
    │    JSONB ingredients amount_g × factor  (NOT recipe_ingredients)      [meal_generator.py:404-427]
    ▼
patient plan: scaled dishes + weekly ingredient checklist    [meal_generator.py:358-364, 667-692]
```

### Explicit non-findings (verified absent)

1. **No runtime bottom-up calculation.** No function in `app/` computes dish nutrition from `recipe_ingredients` × `ingredients`. The only implementation is the offline script (Section 3).
2. **No IFCT data outside the DB + PDF.** No JSON/CSV/Python module embeds IFCT values; the import path is PDF → `ingredients` table only.
3. **Runtime ingredient display does not use the IFCT chain.** Patient-facing ingredient lists and the shopping checklist are built from the legacy `food_items.ingredients` JSONB (Section 4.3). The `recipe_ingredients` table influences the patient experience only indirectly, via the pre-computed `*_per_serving` columns.
