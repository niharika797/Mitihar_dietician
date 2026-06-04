"""
Recalculate food_items nutrition from recipe_ingredients + ingredients data.

Coverage = (ingredients with non-null calories/protein/carbs/fat) / total ingredients for recipe.
  >= 0.80 → recalculate all 5 macros, set nutrition_source = 'calculated'
  <  0.80 → leave macros unchanged,    set nutrition_source = 'manual'
"""
import os, sys
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ["DATABASE_URL"].replace("+asyncpg", "+psycopg2")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

COVERAGE_THRESHOLD = 0.80


def recalculate():
    session = Session()
    try:
        food_item_ids = [row[0] for row in session.execute(
            text("SELECT id FROM food_items ORDER BY id")
        ).fetchall()]

        total            = len(food_item_ids)
        updated          = 0
        left_manual      = 0
        no_ingredients   = 0
        coverage_values  = []   # coverage per recipe that has ingredients

        for i, fid in enumerate(food_item_ids, 1):
            rows = session.execute(text("""
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
            """), {"fid": fid}).fetchall()

            if not rows:
                no_ingredients += 1
                left_manual += 1
                session.execute(text(
                    "UPDATE food_items SET nutrition_source = 'manual' WHERE id = :fid"
                ), {"fid": fid})
                if i % 100 == 0:
                    print(f"  [{i}/{total}] updated={updated} manual={left_manual}")
                continue

            total_ing = len(rows)
            covered   = sum(
                1 for r in rows
                if r[0] is not None and r[1] is not None
                   and r[2] is not None and r[3] is not None
            )
            coverage = covered / total_ing
            coverage_values.append(coverage)

            if coverage >= COVERAGE_THRESHOLD:
                cal = sum((r[0] or 0) * r[5] / 100 for r in rows)
                pro = sum((r[1] or 0) * r[5] / 100 for r in rows)
                crb = sum((r[2] or 0) * r[5] / 100 for r in rows)
                fat = sum((r[3] or 0) * r[5] / 100 for r in rows)
                fib = sum((r[4] or 0) * r[5] / 100 for r in rows)
                session.execute(text("""
                    UPDATE food_items
                    SET cal_per_serving     = :cal,
                        protein_per_serving = :pro,
                        carbs_per_serving   = :crb,
                        fat_per_serving     = :fat,
                        fiber_per_serving   = :fib,
                        nutrition_source    = 'calculated'
                    WHERE id = :fid
                """), {"cal": round(cal, 2), "pro": round(pro, 2), "crb": round(crb, 2),
                       "fat": round(fat, 2), "fib": round(fib, 2), "fid": fid})
                updated += 1
            else:
                session.execute(text(
                    "UPDATE food_items SET nutrition_source = 'manual' WHERE id = :fid"
                ), {"fid": fid})
                left_manual += 1

            if i % 100 == 0:
                session.commit()
                print(f"  [{i}/{total}] updated={updated} manual={left_manual}")

        session.commit()

        avg_coverage = (sum(coverage_values) / len(coverage_values) * 100) if coverage_values else 0

        print("\n=== FINAL STATS ===")
        print(f"Total recipes processed        : {total}")
        print(f"Updated to 'calculated'        : {updated}")
        print(f"Left as 'manual'               : {left_manual}")
        print(f"  of which no ingredients      : {no_ingredients}")
        print(f"  of which low coverage        : {left_manual - no_ingredients}")
        print(f"Average coverage (with ingred) : {avg_coverage:.1f}%")

    finally:
        session.close()


if __name__ == "__main__":
    recalculate()
