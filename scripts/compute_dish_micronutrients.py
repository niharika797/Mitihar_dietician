"""
Compute per-dish micronutrients (iron/calcium/K/P/Zn/free_sugars/saturated_fat) for
food_items from the ingredient chain, and write the food_items *_per_serving columns.

Separate from recalculate_recipe_nutrition.py (which owns macros + nutrition_source) to
avoid coupling — this only fills the IFCT-derived micro columns added in migration a7b8c9d0e1f2.

Per-nutrient GRAM-WEIGHTED coverage gate: a dish's value for nutrient X is written only if
the ingredients that HAVE X data cover >= GATE of the dish's total grams. Otherwise NULL
(unknown, not 0) — so a dish missing its bulk ingredient's data is never filtered on a
falsely-low value. Sodium is intentionally NOT computed (added-salt is unmodeled → unreliable).

Run: python -m scripts.compute_dish_micronutrients          # dry run (stats only)
     python -m scripts.compute_dish_micronutrients --write
"""
import os, sys
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))
from dotenv import load_dotenv; load_dotenv()
from sqlalchemy import create_engine, text

GATE = 0.60   # gram-weighted coverage required to trust a computed nutrient

# food_items column  ->  ingredients column
NUTRIENTS = {
    "iron_per_serving":          "iron_per_100g",
    "calcium_per_serving":       "calcium_per_100g",
    "potassium_per_serving":     "potassium_per_100g",
    "phosphorus_per_serving":    "phosphorus_per_100g",
    "zinc_per_serving":          "zinc_per_100g",
    "free_sugars_per_serving":   "free_sugars_per_100g",
    "saturated_fat_per_serving": "saturated_fat_per_100g",
}


def main() -> None:
    write = "--write" in sys.argv
    eng = create_engine(os.environ["DATABASE_URL"].replace("+asyncpg", "+psycopg2"))
    ing_cols = ", ".join(f"ing.{c}" for c in NUTRIENTS.values())

    with eng.connect() as conn:
        fids = [r[0] for r in conn.execute(text("SELECT id FROM food_items ORDER BY id")).fetchall()]

    filled = {c: 0 for c in NUTRIENTS}
    updates: list[dict] = []
    with eng.connect() as conn:
        for fid in fids:
            rows = conn.execute(text(f"""
                SELECT ri.quantity_g, {ing_cols}
                FROM recipe_ingredients ri JOIN ingredients ing ON ing.id = ri.ingredient_id
                WHERE ri.food_item_id = :fid
            """), {"fid": fid}).fetchall()
            total_g = sum(float(r[0] or 0) for r in rows)
            rec = {"id": fid}
            for idx, (col, _src) in enumerate(NUTRIENTS.items(), start=1):
                if total_g <= 0:
                    rec[col] = None
                    continue
                covered_g = sum(float(r[0] or 0) for r in rows if r[idx] is not None)
                if covered_g / total_g >= GATE:
                    rec[col] = round(sum((r[idx] or 0) * float(r[0] or 0) / 100 for r in rows), 2)
                    filled[col] += 1
                else:
                    rec[col] = None
            updates.append(rec)

    n = len(fids)
    print(f"food_items: {n}")
    for col in NUTRIENTS:
        print(f"  {col:26} computed for {filled[col]} dishes ({filled[col]/n*100:.0f}%)")

    if not write:
        print("\nDry run — pass --write to apply.")
        return

    set_clause = ", ".join(f"{c} = :{c}" for c in NUTRIENTS)
    with eng.begin() as conn:
        for u in updates:
            conn.execute(text(f"UPDATE food_items SET {set_clause} WHERE id = :id"), u)
    print(f"\nWrote micronutrients to {n} food_items.")


if __name__ == "__main__":
    main()
