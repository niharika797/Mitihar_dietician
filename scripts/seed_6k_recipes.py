"""
seed_6k_recipes.py
------------------
Reads the 6K Indian Food Recipes Dataset, fetches per-ingredient nutrition
from USDA FoodData Central, computes per-serving macros, and inserts into
food_items with is_verified=False, source='6k_dataset'.

Usage:
    venv\\Scripts\\python scripts\\seed_6k_recipes.py

Env vars (optional, falls back to hardcoded defaults):
    USDA_API_KEY   — FoodData Central key
    DATABASE_URL   — PostgreSQL DSN
"""

import os
import re
import sys
import time
import json
import urllib.request
import urllib.parse
import logging
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.models.db_models import FoodItem

# ── Config ────────────────────────────────────────────────────────────────────
USDA_API_KEY  = os.getenv("USDA_API_KEY",  "uo7qIJasjbhAa77L7h455qdAvtwXg3l2U9TjaUZ8")
DATABASE_URL  = os.getenv("DATABASE_URL",  "postgresql+psycopg2://admin:mityahar_dev@localhost:5432/mityahar_db")
CSV_PATH      = Path(__file__).parent.parent / "6000+ Indian Food Recipes Dataset" / "IndianFoodDatasetCSV.csv"
CONFIDENCE_THRESHOLD = 0.55   # min fraction of ingredients matched to accept recipe
BATCH_SIZE    = 100            # print progress every N recipes
USDA_DELAY    = 0.25          # seconds between USDA calls (stays under rate limit)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# ── Unit → grams conversion table ────────────────────────────────────────────
UNIT_TO_GRAMS = {
    "cup": 240, "cups": 240,
    "tbsp": 15, "tablespoon": 15, "tablespoons": 15,
    "tsp": 5,   "teaspoon": 5,   "teaspoons": 5,
    "ml": 1,    "l": 1000,
    "g": 1,     "gram": 1,       "grams": 1,
    "kg": 1000, "kilogram": 1000,
    "piece": 80, "pieces": 80,   "whole": 80,
    "bunch": 100, "sprig": 5,
    "leaf": 2,  "leaves": 2,
    "pinch": 0.5, "handful": 30,
    "inch": 10,   "clove": 5,
    "pod": 2,     "stick": 10,
    "strand": 0.1,
}

# ── Slot / diet / region mapping ──────────────────────────────────────────────
COURSE_TO_SLOT = {
    "south indian breakfast": "main_dish",
    "north indian breakfast": "main_dish",
    "indian breakfast":       "main_dish",
    "snack":                  "snack_item",
    "side dish":              "sabzi",
    "main course":            "dal_protein",
    "lunch":                  "grain",
    "dinner":                 "grain",
    "one pot dish":           "one_pot",
}

DIET_MAP = {
    "vegetarian":                   "Vegetarian",
    "high protein vegetarian":      "Vegetarian",
    "non vegeterian":               "Non-Vegetarian",
    "high protein non vegetarian":  "Non-Vegetarian",
    "eggetarian":                   "Eggetarian",
    "diabetic friendly":            "Vegetarian",   # remap to Vegetarian; plan_type handles diabetic
}

CUISINE_TO_REGION = {
    "north indian": "North", "punjabi": "North", "rajasthani": "North",
    "mughlai": "North", "uttar pradesh": "North", "himachal": "North",
    "south indian": "South", "kerala": "South", "tamil": "South",
    "karnataka": "South", "andhra": "South", "chettinad": "South",
    "telangana": "South",
    "bengali": "East",  "odia": "East", "assamese": "East",
    "bihari": "East",   "jharkhand": "East",
    "gujarati": "West", "maharashtrian": "West", "goan": "West",
    "maharashtra": "West", "sindhi": "West",
}

PLAN_TYPE_TAGS_DEFAULT = ["Healthy", "Diabetic-Friendly", "Gym-Friendly"]

# ── USDA cache (avoid re-querying same ingredient) ────────────────────────────
_usda_cache: dict = {}

def usda_lookup(ingredient_name: str) -> dict | None:
    """
    Returns per-100g nutrition dict or None if not found.
    Keys: cal, protein, carbs, fat, fiber, sodium
    """
    key = ingredient_name.lower().strip()
    if key in _usda_cache:
        return _usda_cache[key]

    try:
        query = urllib.parse.quote(key)
        url = (
            f"https://api.nal.usda.gov/fdc/v1/foods/search"
            f"?query={query}&dataType=Foundation,SR%20Legacy&pageSize=1&api_key={USDA_API_KEY}"
        )
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read())

        foods = data.get("foods", [])
        if not foods:
            _usda_cache[key] = None
            return None

        nutrients = {n["nutrientName"]: n["value"] for n in foods[0].get("foodNutrients", [])}
        result = {
            "cal":     nutrients.get("Energy", 0) or 0,
            "protein": nutrients.get("Protein", 0) or 0,
            "carbs":   nutrients.get("Carbohydrate, by difference", 0) or 0,
            "fat":     nutrients.get("Total lipid (fat)", 0) or 0,
            "fiber":   nutrients.get("Fiber, total dietary", 0) or 0,
            "sodium":  nutrients.get("Sodium, Na", 0) or 0,
        }
        _usda_cache[key] = result
        time.sleep(USDA_DELAY)
        return result

    except Exception as e:
        log.debug(f"USDA lookup failed for '{ingredient_name}': {e}")
        _usda_cache[key] = None
        return None


# ── Ingredient string parser ──────────────────────────────────────────────────
_SKIP_WORDS = {"salt", "water", "oil", "taste", "required", "needed",
               "as needed", "to taste", "as required", "as per taste"}

def parse_ingredient_line(line: str) -> tuple[float | None, str | None]:
    """
    Returns (total_grams, clean_name) or (None, None) if unparseable / skip.
    """
    line = line.strip().rstrip(",")
    if not line:
        return None, None

    # Skip vague lines
    if any(skip in line.lower() for skip in _SKIP_WORDS):
        return None, None

    # Pattern: optional_qty  optional_unit  ingredient_name  optional_description
    m = re.match(
        r'^([\d./]+(?:\s*-\s*[\d./]+)?)\s*([a-zA-Z]+)?\s+(.+?)(?:\s*[-–,].*)?$',
        line.strip(),
        re.IGNORECASE,
    )
    if not m:
        return None, None

    qty_str, unit_str, name = m.group(1).strip(), (m.group(2) or "").lower().strip(), m.group(3).strip()

    # Parse quantity
    try:
        if "/" in qty_str:
            num, den = qty_str.split("/", 1)
            qty = float(num.strip()) / float(den.strip())
        elif "-" in qty_str:
            lo, hi = qty_str.split("-", 1)
            qty = (float(lo.strip()) + float(hi.strip())) / 2
        else:
            qty = float(qty_str)
    except ValueError:
        return None, None

    # Resolve unit
    grams_per_unit = UNIT_TO_GRAMS.get(unit_str)
    if grams_per_unit is None:
        # unit_str is likely part of ingredient name (e.g. "2 Onion")
        name = f"{unit_str} {name}".strip() if unit_str else name
        grams_per_unit = UNIT_TO_GRAMS["piece"]  # default piece weight

    total_grams = qty * grams_per_unit

    # Clean name: drop everything after dash/comma/parenthesis
    clean = re.sub(r"\s*[-–(,].*", "", name).strip().lower().capitalize()
    if not clean or len(clean) < 2:
        return None, None

    return total_grams, clean

# ── Nutrition calculator ──────────────────────────────────────────────────────
def compute_recipe_nutrition(ingredient_str: str, servings: int) -> dict | None:
    """
    Parses ingredient string, fetches USDA nutrition per ingredient,
    returns per-serving totals plus confidence score. Returns None if
    confidence < CONFIDENCE_THRESHOLD.
    """
    lines = [l.strip() for l in ingredient_str.split(",") if l.strip()]
    if not lines:
        return None

    totals = {"cal": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0, "fiber": 0.0, "sodium": 0.0}
    parsed_ingredients = []
    matched = 0

    for line in lines:
        grams, name = parse_ingredient_line(line)
        if grams is None or name is None:
            continue   # skip salt / water / unparseable

        parsed_ingredients.append({"name": name, "amount_g": round(grams, 1)})

        nutrition = usda_lookup(name)
        if nutrition:
            factor = grams / 100.0
            for key in totals:
                totals[key] += nutrition[key] * factor
            matched += 1

    if not parsed_ingredients:
        return None

    confidence = matched / len(parsed_ingredients)
    if confidence < CONFIDENCE_THRESHOLD:
        return None

    servings = max(1, servings)
    return {
        "cal_per_serving":     round(totals["cal"]     / servings, 2),
        "protein_per_serving": round(totals["protein"] / servings, 2),
        "carbs_per_serving":   round(totals["carbs"]   / servings, 2),
        "fat_per_serving":     round(totals["fat"]      / servings, 2),
        "fiber_per_serving":   round(totals["fiber"]   / servings, 2),
        "sodium_per_serving":  round(totals["sodium"]  / servings, 2),
        "ingredients":         parsed_ingredients,
        "confidence":          round(confidence, 2),
    }


# ── Region detector ───────────────────────────────────────────────────────────
def detect_region(cuisine: str) -> list[str]:
    cuisine_lower = cuisine.lower()
    for keyword, region in CUISINE_TO_REGION.items():
        if keyword in cuisine_lower:
            return [region]
    return ["North", "South", "East", "West"]   # generic Indian → all regions


# ── Meal time tags ────────────────────────────────────────────────────────────
def course_to_meal_time_tags(course: str) -> list[str]:
    c = course.lower()
    if "breakfast" in c:
        return ["Breakfast"]
    if c == "snack":
        return ["Morning_Snack", "Evening_Snack"]
    if c in ("lunch", "main course"):
        return ["Lunch", "Dinner"]
    if c == "dinner":
        return ["Dinner"]
    if c == "side dish":
        return ["Lunch", "Dinner"]
    if c == "one pot dish":
        return ["Lunch", "Dinner"]
    return ["Lunch", "Dinner"]

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if not CSV_PATH.exists():
        log.error(f"Dataset not found at {CSV_PATH}")
        sys.exit(1)

    log.info(f"Loading dataset from {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)
    log.info(f"Total rows: {len(df)}")

    # Filter to usable Indian recipes
    indian_cuisines = df["Cuisine"].str.contains(
        "Indian|North Indian|South Indian|Bengali|Kerala|Tamil|Karnataka|"
        "Rajasthani|Andhra|Gujarati|Goan|Punjabi|Chettinad|Maharashtra|"
        "Hyderabad|Mughlai|Odia|Assamese|Bihari|Sindhi|Himachal|Telangana",
        case=False, na=False,
    )
    meal_courses = df["Course"].isin([
        "Lunch", "Dinner", "Side Dish", "Snack",
        "South Indian Breakfast", "North Indian Breakfast",
        "Indian Breakfast", "Main Course", "One Pot Dish",
    ])
    valid_diet = df["Diet"].isin([
        "Vegetarian", "High Protein Vegetarian",
        "Non Vegeterian", "High Protein Non Vegetarian",
        "Eggetarian", "Diabetic Friendly",
    ])
    valid_servings = pd.to_numeric(df["Servings"], errors="coerce").between(1, 10)

    candidates = df[indian_cuisines & meal_courses & valid_diet & valid_servings].copy()
    candidates["Servings"] = pd.to_numeric(candidates["Servings"], errors="coerce").fillna(4).astype(int)

    # Sort: recipes with gram measurements first (highest confidence first)
    candidates["_has_grams"] = candidates["TranslatedIngredients"].str.contains(
        r"\d+\s*grams?", case=False, na=False
    )
    candidates = candidates.sort_values("_has_grams", ascending=False).reset_index(drop=True)
    log.info(f"Filtered candidates: {len(candidates)}")

    # DB setup
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    inserted = 0
    skipped_confidence = 0
    skipped_duplicate = 0
    skipped_zero_cal = 0
    errors = 0

    try:
        for i, row in candidates.iterrows():
            recipe_name = str(row.get("TranslatedRecipeName", "")).strip()
            if not recipe_name:
                continue

            course    = str(row.get("Course", "")).strip()
            cuisine   = str(row.get("Cuisine", "")).strip()
            diet_raw  = str(row.get("Diet", "")).strip().lower()
            servings  = int(row.get("Servings", 4))
            ing_str   = str(row.get("TranslatedIngredients", ""))
            instr     = str(row.get("TranslatedInstructions", ""))

            diet_type      = DIET_MAP.get(diet_raw, "Vegetarian")
            slot_type      = COURSE_TO_SLOT.get(course.lower(), "grain")
            region_tags    = detect_region(cuisine)
            meal_time_tags = course_to_meal_time_tags(course)

            # Duplicate check
            exists = session.query(FoodItem.id).filter(
                FoodItem.recipe_name == recipe_name,
                FoodItem.diet_type   == diet_type,
            ).first()
            if exists:
                skipped_duplicate += 1
                continue

            # Compute nutrition via USDA
            nutrition = compute_recipe_nutrition(ing_str, servings)
            if nutrition is None:
                skipped_confidence += 1
                continue

            if nutrition["cal_per_serving"] <= 0:
                skipped_zero_cal += 1
                continue

            food_item = FoodItem(
                recipe_name         = recipe_name,
                slot_type           = slot_type,
                cal_per_serving     = nutrition["cal_per_serving"],
                protein_per_serving = nutrition["protein_per_serving"],
                carbs_per_serving   = nutrition["carbs_per_serving"],
                fat_per_serving     = nutrition["fat_per_serving"],
                fiber_per_serving   = nutrition["fiber_per_serving"],
                sodium_per_serving  = nutrition["sodium_per_serving"],
                diet_type           = diet_type,
                region_tags         = region_tags,
                meal_time_tags      = meal_time_tags,
                plan_type_tags      = PLAN_TYPE_TAGS_DEFAULT,
                ingredients         = nutrition["ingredients"],
                instructions        = instr[:2000] if instr else "",
                source              = "6k_dataset",
                is_verified         = False,
            )

            try:
                session.add(food_item)
                session.commit()
                inserted += 1
            except Exception as e:
                session.rollback()
                log.debug(f"Insert failed for '{recipe_name}': {e}")
                errors += 1

            if (i + 1) % BATCH_SIZE == 0:
                log.info(
                    f"  Progress {i+1}/{len(candidates)} | "
                    f"inserted={inserted} skipped_conf={skipped_confidence} "
                    f"dupes={skipped_duplicate}"
                )

    finally:
        session.close()

    print("\n" + "=" * 55)
    print(f"  SEED COMPLETE")
    print(f"  Inserted:           {inserted}")
    print(f"  Skipped (low conf): {skipped_confidence}")
    print(f"  Skipped (zero cal): {skipped_zero_cal}")
    print(f"  Skipped (dupes):    {skipped_duplicate}")
    print(f"  Errors:             {errors}")
    print(f"  USDA cache size:    {len(_usda_cache)} unique ingredients looked up")
    print("=" * 55)


if __name__ == "__main__":
    main()
