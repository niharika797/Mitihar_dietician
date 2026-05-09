"""
fix_6k_calories.py  (v2 — full rewrite)
----------------------------------------
Fixes inflated cal_per_serving for all source='6k_dataset' rows.

ROOT CAUSE OF ORIGINAL BUG:
  seed_6k_recipes.py used cup=240g for EVERY ingredient (water density).
  Dense ingredients like flour (120g/cup), besan (92g/cup), dal (192g/cup)
  were over-weighted by up to 2×, doubling reported calories.

WHY THE FIRST fix_6k_calories.py DID NOTHING:
  It called recompute_nutrition(ingredients_json) which re-used the already-
  stored (wrong) amount_g values from the DB. INGREDIENT_CUP_GRAMS was
  defined but never applied in that code path. Fetching USDA again with the
  same wrong grams produces the same wrong calories.

CORRECT APPROACH (this script):
  1. Load original CSV (source of truth for ingredient strings + servings)
  2. For each 6k_dataset row in DB, find its CSV row by recipe_name
  3. Re-PARSE the original ingredient string with ingredient-aware cup weights
  4. Re-fetch USDA nutrition using corrected gram amounts
  5. UPDATE both cal_per_serving AND ingredients JSONB in the DB
  6. DELETE rows that are still > CAL_CAP after the fix (unverifiable outliers)

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

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.models.db_models import FoodItem

# ── Config ────────────────────────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. Add it to your .env file.")
DATABASE_URL = DATABASE_URL.replace("+asyncpg", "+psycopg2")

USDA_API_KEY = os.getenv("USDA_API_KEY")
if not USDA_API_KEY:
    raise RuntimeError(
        "USDA_API_KEY is not set. Add it to your .env file.\n"
        "Get a free key at: https://fdc.nal.usda.gov/api-key-signup.html"
    )
CSV_PATH     = Path(__file__).parent.parent / "data" / "6000+ Indian Food Recipes Dataset" / "IndianFoodDatasetCSV.csv"
USDA_DELAY   = 0.05
CAL_CAP      = 1200
CONFIDENCE_THRESHOLD = 0.50

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# ── Ingredient-aware cup densities (g per 1 cup) ─────────────────────────────
# This is the key correction over the original seed script.
INGREDIENT_CUP_GRAMS = {
    # Flours & grains
    "flour":            120,
    "wheat flour":      120,
    "maida":            120,
    "besan":             92,
    "gram flour":        92,
    "rice flour":       158,
    "rice":             185,   # dry raw rice
    "poha":              90,
    "oats":              80,
    "semolina":         167,
    "sooji":            167,
    "rava":             167,
    "cornmeal":         122,
    "bread crumbs":     108,
    # Fats
    "oil":              218,
    "ghee":             218,
    "butter":           227,
    # Dairy
    "milk":             244,
    "curd":             245,
    "yogurt":           245,
    "cream":            238,
    "paneer":           240,
    # Pulses & lentils
    "dal":              192,
    "lentil":           192,
    "lentils":          192,
    "chana":            200,
    "chickpea":         200,
    "rajma":            185,
    "moong":            192,
    "urad":             192,
    # Sugars
    "sugar":            200,
    "jaggery":          220,
    "honey":            340,
    # Vegetables (chopped)
    "onion":            160,
    "tomato":           180,
    "spinach":           30,   # fresh leaves pack loosely
    "palak":             30,
    "methi":             35,
    "cabbage":           90,
    "carrot":           128,
    "peas":             145,
    # Coconut
    "coconut":           80,   # grated fresh
    "coconut milk":     240,   # liquid
    # Nuts & seeds
    "cashew":           130,
    "peanut":           146,
    "sesame":           144,
    "almond":            92,
}

# Default units table (fallback when ingredient not in above dict)
UNIT_TO_GRAMS = {
    "cup": 240, "cups": 240,       # overridden per-ingredient via INGREDIENT_CUP_GRAMS
    "tbsp": 15, "tablespoon": 15, "tablespoons": 15,
    "tsp": 5,   "teaspoon": 5,   "teaspoons": 5,
    "ml": 1,    "l": 1000,
    "g": 1,     "gram": 1,       "grams": 1,
    "kg": 1000, "kilogram": 1000,
    "piece": 80, "pieces": 80,   "whole": 80,
    "bunch": 100, "sprig": 5,
    "leaf": 2,   "leaves": 2,
    "pinch": 0.5, "handful": 30,
    "inch": 10,   "clove": 5,
    "pod": 2,     "stick": 10,
    "strand": 0.1,
}

_SKIP_WORDS = {
    "salt", "water", "taste", "required", "needed",
    "as needed", "to taste", "as required", "as per taste",
    "for garnish", "for serving",
}

# ── USDA cache ────────────────────────────────────────────────────────────────
_usda_cache: dict = {}

def usda_lookup(ingredient_name: str) -> dict | None:
    key = ingredient_name.lower().strip()
    if key in _usda_cache:
        return _usda_cache[key]
    try:
        url = (
            f"https://api.nal.usda.gov/fdc/v1/foods/search"
            f"?query={urllib.parse.quote(key)}"
            f"&dataType=Foundation,SR%20Legacy&pageSize=1&api_key={USDA_API_KEY}"
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
        log.debug(f"USDA miss: '{ingredient_name}' — {e}")
        _usda_cache[key] = None
        return None


# ── Corrected ingredient parser (uses INGREDIENT_CUP_GRAMS) ──────────────────
def get_cup_grams(ingredient_name: str) -> float:
    name_lower = ingredient_name.lower()
    for keyword, grams in INGREDIENT_CUP_GRAMS.items():
        if keyword in name_lower:
            return float(grams)
    return 240.0   # safe default for liquid-like ingredients


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
        # ← THE KEY FIX: use ingredient-aware cup weight
        grams_per_unit = get_cup_grams(name)
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


def recompute_from_string(ingredient_str: str, servings: int) -> dict | None:
    """Full re-parse from original CSV ingredient string → corrected nutrition."""
    lines = [l.strip() for l in ingredient_str.split(",") if l.strip()]
    if not lines:
        return None

    totals = {"cal": 0.0, "protein": 0.0, "carbs": 0.0,
              "fat": 0.0, "fiber": 0.0, "sodium": 0.0}
    parsed = []
    matched = 0

    for line in lines:
        grams, name = parse_ingredient_line(line)
        if grams is None or name is None:
            continue
        parsed.append({"name": name, "amount_g": round(grams, 1)})
        nutrition = usda_lookup(name)
        if nutrition:
            factor = grams / 100.0
            for k in totals:
                totals[k] += nutrition[k] * factor
            matched += 1

    if not parsed:
        return None

    confidence = matched / len(parsed)
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
        "ingredients":         parsed,
    }


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    if not CSV_PATH.exists():
        log.error(f"CSV not found at {CSV_PATH}")
        sys.exit(1)

    # ── Step 1: Build CSV lookup ──────────────────────────────────────────────
    log.info("Loading original CSV for ingredient strings + servings...")
    df = pd.read_csv(CSV_PATH)
    df["Servings"] = pd.to_numeric(df["Servings"], errors="coerce").fillna(4).astype(int)

    csv_lookup: dict[str, tuple[str, int]] = {}
    for _, row in df.iterrows():
        name = str(row.get("TranslatedRecipeName", "")).strip()
        if name:
            csv_lookup[name] = (
                str(row.get("TranslatedIngredients", "")),
                int(row.get("Servings", 4)),
            )
    log.info(f"CSV index built: {len(csv_lookup)} recipes")

    # ── Step 2: Load all 6k_dataset rows from DB ──────────────────────────────
    engine  = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    rows = session.query(FoodItem).filter(FoodItem.source == "6k_dataset").all()
    log.info(f"DB rows to fix: {len(rows)}")

    # ── Step 3: PRE-WARM USDA CACHE ───────────────────────────────────────────
    # Collect every unique ingredient name across all matched CSV rows FIRST.
    # Then hit the USDA API once per unique ingredient in one concentrated pass.
    # After this, recompute_from_string() makes zero API calls — pure cache hits.
    log.info("Pre-warming USDA cache from all matched recipe ingredients...")
    unique_ingredients: set[str] = set()

    for item in rows:
        csv_row = csv_lookup.get(item.recipe_name)
        if not csv_row:
            continue
        ing_str, _ = csv_row
        for line in ing_str.split(","):
            _, name = parse_ingredient_line(line.strip())
            if name:
                unique_ingredients.add(name.lower().strip())

    log.info(f"Unique ingredients to look up: {len(unique_ingredients)}")

    for i, ingredient in enumerate(sorted(unique_ingredients), 1):
        usda_lookup(ingredient)   # result stored in _usda_cache
        if i % 100 == 0:
            log.info(f"  USDA cache: {i}/{len(unique_ingredients)} ingredients loaded")

    log.info(f"Cache warm. {len(_usda_cache)} entries ({sum(1 for v in _usda_cache.values() if v)} hits, {sum(1 for v in _usda_cache.values() if not v)} misses)")

    # ── Step 4: Process rows — all nutrition from cache, zero API calls ───────
    log.info("Processing DB rows (all from cache, no API calls)...")

    updated       = 0
    deleted       = 0
    no_csv_match  = 0
    low_conf      = 0
    already_ok    = 0
    errors        = 0
    COMMIT_BATCH  = 50   # commit every N rows instead of one per row

    for i, item in enumerate(rows):
        try:
            csv_row = csv_lookup.get(item.recipe_name)
            if not csv_row:
                no_csv_match += 1
                continue

            ing_str, servings = csv_row
            new_nutrition = recompute_from_string(ing_str, servings)

            if new_nutrition is None:
                session.delete(item)
                low_conf += 1
                continue

            new_cal = new_nutrition["cal_per_serving"]

            if new_cal > CAL_CAP:
                session.delete(item)
                deleted += 1
                continue

            old_cal = float(item.cal_per_serving)
            change_pct = abs(new_cal - old_cal) / max(old_cal, 1) * 100
            if change_pct < 5:
                already_ok += 1
                continue

            item.cal_per_serving     = new_nutrition["cal_per_serving"]
            item.protein_per_serving = new_nutrition["protein_per_serving"]
            item.carbs_per_serving   = new_nutrition["carbs_per_serving"]
            item.fat_per_serving     = new_nutrition["fat_per_serving"]
            item.fiber_per_serving   = new_nutrition["fiber_per_serving"]
            item.sodium_per_serving  = new_nutrition["sodium_per_serving"]
            item.ingredients         = new_nutrition["ingredients"]
            updated += 1

        except Exception as e:
            session.rollback()
            log.warning(f"Error on '{item.recipe_name}': {e}")
            errors += 1
            continue

        # Batch commit every COMMIT_BATCH rows
        if (i + 1) % COMMIT_BATCH == 0:
            session.commit()
            log.info(f"  Progress {i+1}/{len(rows)} | updated={updated} deleted={deleted+low_conf} skipped={already_ok}")

    # Final commit for remainder
    session.commit()
    session.close()

    total = len(rows)
    print("\n" + "=" * 58)
    print("  FIX COMPLETE")
    print(f"  Total 6k_dataset rows processed : {total}")
    print(f"  Updated (calories corrected)     : {updated}")
    print(f"  Already within range (<5% change): {already_ok}")
    print(f"  Deleted (still > {CAL_CAP} kcal)      : {deleted}")
    print(f"  Deleted (low confidence reparse) : {low_conf}")
    print(f"  Skipped (no CSV match)           : {no_csv_match}")
    print(f"  Errors                           : {errors}")
    print(f"  USDA cache size                  : {len(_usda_cache)} unique ingredients")
    print("=" * 58)
    print()
    print("Verification SQL:")
    print("  SELECT ROUND(AVG(cal_per_serving),1) AS avg_cal,")
    print("         ROUND(MIN(cal_per_serving),1) AS min_cal,")
    print("         ROUND(MAX(cal_per_serving),1) AS max_cal,")
    print("         COUNT(*) AS total_rows")
    print("  FROM food_items WHERE source = '6k_dataset';")
    print()
    print("Expected: avg_cal between 200–550 kcal/serving")


if __name__ == "__main__":
    main()
