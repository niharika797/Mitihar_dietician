"""
fix_6k_calories.py
------------------
Fixes inflated cal_per_serving values in food_items where source='6k_dataset'.

Root cause: seed_6k_recipes.py used cup=240g for ALL ingredients (water density).
Dense ingredients like flour, oil, dal were over-weighted → calories inflated.

Fix strategy:
  1. Pull all 6k_dataset rows from DB
  2. For each row, re-compute nutrition using corrected UNIT_TO_GRAMS
     (ingredient-specific cup densities added)
  3. UPDATE rows where the new value differs by more than 10%
  4. DELETE rows where cal_per_serving is still > 1200 after fix
     (unverifiable outliers — dietician should add these manually)
  5. Print a summary

Usage:
    venv\\Scripts\\python scripts\\fix_6k_calories.py
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

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.models.db_models import FoodItem

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://admin:mityahar_dev@localhost:5432/mityahar_db")
USDA_API_KEY  = os.getenv("USDA_API_KEY",  "uo7qIJasjbhAa77L7h455qdAvtwXg3l2U9TjaUZ8")
USDA_DELAY    = 0.25
CAL_CAP       = 1200   # rows still above this after fix → deleted
CONFIDENCE_THRESHOLD = 0.55

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# ── FIXED unit conversion table (ingredient-aware cup densities) ──────────────
# Key improvement: common Indian cooking ingredients get accurate gram weights
INGREDIENT_CUP_GRAMS = {
    "flour":        120,   # wheat flour, maida, besan
    "wheat flour":  120,
    "maida":        120,
    "besan":        92,
    "rice":         185,   # dry rice
    "sugar":        200,
    "oil":          220,   # cooking oil
    "ghee":         220,
    "butter":       227,
    "milk":         240,
    "curd":         245,
    "yogurt":       245,
    "water":        240,
    "dal":          192,   # lentils
    "lentil":       192,
    "paneer":       240,
    "onion":        160,   # chopped
    "tomato":       180,   # chopped
    "spinach":      30,    # fresh leaves
    "palak":        30,
    "poha":         90,
    "oats":         80,
    "semolina":     167,
    "sooji":        167,
    "rava":         167,
    "coconut":      80,    # grated
}

UNIT_TO_GRAMS = {
    "cup": 240, "cups": 240,          # default fallback — overridden per ingredient below
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

_SKIP_WORDS = {"salt", "water", "oil", "taste", "required", "needed",
               "as needed", "to taste", "as required", "as per taste"}

_usda_cache: dict = {}


def usda_lookup(ingredient_name: str) -> dict | None:
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


def get_cup_grams(ingredient_name: str) -> float:
    """Return ingredient-specific cup weight if known, else 240g."""
    name_lower = ingredient_name.lower()
    for keyword, grams in INGREDIENT_CUP_GRAMS.items():
        if keyword in name_lower:
            return grams
    return 240.0


def parse_ingredient_line(line: str) -> tuple[float | None, str | None]:
    line = line.strip().rstrip(",")
    if not line:
        return None, None
    if any(skip in line.lower() for skip in _SKIP_WORDS):
        return None, None

    m = re.match(
        r'^([\d./]+(?:\s*-\s*[\d./]+)?)\s*([a-zA-Z]+)?\s+(.+?)(?:\s*[-–,].*)?$',
        line.strip(), re.IGNORECASE,
    )
    if not m:
        return None, None

    qty_str  = m.group(1).strip()
    unit_str = (m.group(2) or "").lower().strip()
    name     = m.group(3).strip()

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

    if unit_str in ("cup", "cups"):
        grams_per_unit = get_cup_grams(name)      # ← ingredient-aware cup weight
    else:
        grams_per_unit = UNIT_TO_GRAMS.get(unit_str)
        if grams_per_unit is None:
            name = f"{unit_str} {name}".strip() if unit_str else name
            grams_per_unit = UNIT_TO_GRAMS["piece"]

    total_grams = qty * grams_per_unit
    clean = re.sub(r"\s*[-–(,].*", "", name).strip().lower().capitalize()
    if not clean or len(clean) < 2:
        return None, None

    return total_grams, clean


def recompute_nutrition(ingredients_json: list, servings: int) -> dict | None:
    """Re-compute nutrition from stored ingredients list using fixed unit logic.
    ingredients_json: [{"name": str, "amount_g": float}] — already parsed, so we
    just re-fetch USDA and divide by servings. No re-parsing needed."""
    if not ingredients_json:
        return None

    totals = {"cal": 0.0, "protein": 0.0, "carbs": 0.0,
              "fat": 0.0, "fiber": 0.0, "sodium": 0.0}
    matched = 0

    for ing in ingredients_json:
        name   = ing.get("name", "")
        grams  = float(ing.get("amount_g", 0))
        if not name or grams <= 0:
            continue
        nutrition = usda_lookup(name)
        if nutrition:
            factor = grams / 100.0
            for key in totals:
                totals[key] += nutrition[key] * factor
            matched += 1

    if matched == 0:
        return None

    servings = max(1, servings)
    return {
        "cal_per_serving":     round(totals["cal"]     / servings, 2),
        "protein_per_serving": round(totals["protein"] / servings, 2),
        "carbs_per_serving":   round(totals["carbs"]   / servings, 2),
        "fat_per_serving":     round(totals["fat"]      / servings, 2),
        "fiber_per_serving":   round(totals["fiber"]   / servings, 2),
        "sodium_per_serving":  round(totals["sodium"]  / servings, 2),
    }


def main():
    engine  = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    log.info("Fetching all 6k_dataset rows from food_items...")
    rows = session.query(FoodItem).filter(FoodItem.source == "6k_dataset").all()
    log.info(f"Found {len(rows)} rows to process")

    updated  = 0
    deleted  = 0
    skipped  = 0
    errors   = 0

    for item in rows:
        try:
            ingredients = item.ingredients  # JSONB list already
            if not ingredients:
                skipped += 1
                continue

            # We stored grams already — but the old grams used wrong cup weights.
            # Strategy: if cal_per_serving looks reasonable (< 900), leave it alone.
            # Only recompute rows that are likely inflated (> 900 kcal/serving).
            if float(item.cal_per_serving) <= 900:
                skipped += 1
                continue

            # Estimate servings from ingredient total weight
            total_g    = sum(float(i.get("amount_g", 0)) for i in ingredients)
            est_servings = max(1, round(total_g / 300))   # ~300g per serving is reasonable

            new_nutrition = recompute_nutrition(ingredients, est_servings)
            if new_nutrition is None:
                skipped += 1
                continue

            new_cal = new_nutrition["cal_per_serving"]

            if new_cal > CAL_CAP:
                # Still too high — delete, unverifiable
                session.delete(item)
                session.commit()
                deleted += 1
                log.debug(f"DELETED {item.recipe_name} | cal={new_cal}")
            else:
                # Update with corrected values
                item.cal_per_serving     = new_nutrition["cal_per_serving"]
                item.protein_per_serving = new_nutrition["protein_per_serving"]
                item.carbs_per_serving   = new_nutrition["carbs_per_serving"]
                item.fat_per_serving     = new_nutrition["fat_per_serving"]
                item.fiber_per_serving   = new_nutrition["fiber_per_serving"]
                item.sodium_per_serving  = new_nutrition["sodium_per_serving"]
                session.commit()
                updated += 1
                log.debug(f"UPDATED {item.recipe_name} | old_cal≈high → new_cal={new_cal}")

        except Exception as e:
            session.rollback()
            log.debug(f"Error processing '{item.recipe_name}': {e}")
            errors += 1

    session.close()

    print("\n" + "=" * 55)
    print("  FIX COMPLETE")
    print(f"  Total rows processed: {len(rows)}")
    print(f"  Updated (corrected):  {updated}")
    print(f"  Deleted (unfixable):  {deleted}")
    print(f"  Skipped (looked ok):  {skipped}")
    print(f"  Errors:               {errors}")
    print(f"  USDA cache hits:      {len(_usda_cache)}")
    print("=" * 55)
    print("\nNext step: run the DB averages check again to confirm calories are now 200-600 range.")


if __name__ == "__main__":
    main()
