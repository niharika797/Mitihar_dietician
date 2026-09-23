"""
Backfill the recipe_ingredients gap found by find_dropped_recipe_ingredients.py
for the 5 dishes that actually have one (1789, 1779, 3201, 3411, 3418).

Each dish's food_items.ingredients JSONB has an entry whose name is a parsing
artifact from the original ingest ("To 10 cashew nuts", "Gm arhar dal", "To 3
cloves", "To 3 garlic" -- a stray connector/unit word glued onto the real
ingredient name and count). Each artifact name has its OWN row in
`ingredients` with usable nutrition (e.g. id 849 "To 10 cashew nuts", 553.3
kcal/100g) -- so `find_dropped_recipe_ingredients.py` reported these as
"would_now_match" even though the real gap is that seed_recipe_ingredients.py
was never re-run for these 5 dishes after those rows existed. Re-linking to
the ARTIFACT row would keep the duplicate; this instead points each dish at
the existing clean canonical ingredient and a realistic gram quantity for the
stated count, sourced from standard weight references (see WEB_SOURCES).

WEB_SOURCES (verified 2026-08-04):
  - garlic clove ~3g            https://tastylicious.com/how-much-does-a-garlic-clove-weigh/
  - cashew nut ~1.5g            https://snackygrams.com/blogs/news/calories-in-one-cashew-nut
  - toor/arhar dal, rasam-for-4 ~20-25g total  https://www.indianhealthyrecipes.com/toor-dal-arhar-dal/
  - whole clove (spice) ~0.15-0.2g each, standard kitchen reference

FIXES (food_item_ids -> canonical ingredient_id, quantity_g):
  1789, 1779  Corn Palak                  -> 204 Cashew nuts   15.0   (10 x 1.5g)
  3201        Thakkali Rasam              -> 108 Arhar dal     20.0   (mid-point of 20-25g/batch,
                                                                        proportionate to this dish's
                                                                        existing 40g tomato quantity)
  3411, 3418  Nawabi Mixed Vegetable Gravy -> 378 garlic        9.0   (3 x 3g)
  3411, 3418  Nawabi Mixed Vegetable Gravy -> 241 Cloves        0.5   (3 x ~0.15g, whole spice --
                                                                        distinct ingredient from garlic,
                                                                        both existed as separate JSONB
                                                                        lines in the original recipe)

After inserting, recomputes cal_per_serving/protein/carbs/fat/fiber for just
these 5 food_items using the same coverage-gated formula as
scripts/recalculate_recipe_nutrition.py (>=80% of linked ingredients have
full macro data -> recalculate; else leave as-is) -- scoped to these 5 rows
only, not a full-table recalculation.

Usage:
    python -m scripts.backfill_gap_dish_ingredients            # dry run
    python -m scripts.backfill_gap_dish_ingredients --write
"""
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
sys.path.insert(0, str(PROJECT_ROOT))

import os
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ["DATABASE_URL"].replace("+asyncpg", "+psycopg2")
COVERAGE_THRESHOLD = 0.80

# (food_item_id, ingredient_id, quantity_g)
FIXES = [
    (1789, 204, 15.0),
    (1779, 204, 15.0),
    (3201, 108, 20.0),
    (3411, 378, 9.0),
    (3411, 241, 0.5),
    (3418, 378, 9.0),
    (3418, 241, 0.5),
]


def main() -> None:
    write = "--write" in sys.argv
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        pair_filter = " OR ".join(f"(food_item_id = {f} AND ingredient_id = {i})" for f, i, _ in FIXES)
        already = set(conn.execute(text(
            f"SELECT food_item_id, ingredient_id FROM recipe_ingredients WHERE {pair_filter}"
        )).fetchall())

        to_insert = [(f, i, q) for f, i, q in FIXES if (f, i) not in already]
        print(f"{len(to_insert)}/{len(FIXES)} rows to insert (rest already linked):")
        for f, i, q in to_insert:
            print(f"  food_item_id={f} ingredient_id={i} quantity_g={q}")

        if not write:
            print("\nDRY RUN. Re-run with --write to apply.")
            return

        for f, i, q in to_insert:
            conn.execute(text("""
                INSERT INTO recipe_ingredients (food_item_id, ingredient_id, quantity_g)
                VALUES (:fid, :iid, :qty)
            """), {"fid": f, "iid": i, "qty": q})

        target_ids = sorted({f for f, _, _ in FIXES})
        for fid in target_ids:
            rows = conn.execute(text("""
                SELECT ing.calories_per_100g, ing.protein_per_100g, ing.carbs_per_100g,
                       ing.fat_per_100g, ing.fiber_per_100g, ri.quantity_g
                FROM recipe_ingredients ri JOIN ingredients ing ON ing.id = ri.ingredient_id
                WHERE ri.food_item_id = :fid
            """), {"fid": fid}).fetchall()
            covered = sum(1 for r in rows if None not in r[:4])
            coverage = covered / len(rows) if rows else 0
            if coverage >= COVERAGE_THRESHOLD:
                cal = sum((r[0] or 0) * r[5] / 100 for r in rows)
                pro = sum((r[1] or 0) * r[5] / 100 for r in rows)
                crb = sum((r[2] or 0) * r[5] / 100 for r in rows)
                fat = sum((r[3] or 0) * r[5] / 100 for r in rows)
                fib = sum((r[4] or 0) * r[5] / 100 for r in rows)
                conn.execute(text("""
                    UPDATE food_items SET cal_per_serving = :cal, protein_per_serving = :pro,
                        carbs_per_serving = :crb, fat_per_serving = :fat, fiber_per_serving = :fib,
                        nutrition_source = 'calculated'
                    WHERE id = :fid
                """), {"cal": round(cal, 2), "pro": round(pro, 2), "crb": round(crb, 2),
                       "fat": round(fat, 2), "fib": round(fib, 2), "fid": fid})
                print(f"food_item_id={fid}: recalculated, coverage={coverage:.0%}, cal={round(cal, 2)}")
            else:
                print(f"food_item_id={fid}: coverage={coverage:.0%} < {COVERAGE_THRESHOLD:.0%}, left unchanged")

    print("done." if write else "")


if __name__ == "__main__":
    main()
