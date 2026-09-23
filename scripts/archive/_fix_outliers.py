"""
Task 4A: Fix outliers.
1. Fix saffron strands: calories_per_100g 24200 → 310
2. Revert 30 outlier recipes (cal > 1500 or cal < 50) to nutrition_source='manual'
   so they use their original hand-entered values rather than bad calculated values.
3. Re-run recalculation for saffron-affected recipes (Tandoori Paneer).
"""
import os, sys
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))
from dotenv import load_dotenv; load_dotenv()
from sqlalchemy import create_engine, text

engine = create_engine(os.environ["DATABASE_URL"].replace("+asyncpg", "+psycopg2"))

with engine.begin() as conn:
    # 1. Fix saffron: LLM estimated 24200 kcal/100g → correct is ~310 kcal/100g
    result = conn.execute(text(
        "UPDATE ingredients SET calories_per_100g = 310 WHERE LOWER(name) LIKE '%saffron%'"
    ))
    print(f"Saffron rows fixed: {result.rowcount}")

    # 2. Revert outlier food_items to 'manual'
    result = conn.execute(text("""
        UPDATE food_items
        SET nutrition_source = 'manual'
        WHERE nutrition_source = 'calculated'
          AND (cal_per_serving < 50 OR cal_per_serving > 1500)
    """))
    reverted = result.rowcount
    print(f"Outlier recipes reverted to 'manual': {reverted}")

    # 3. Re-run calculation only for recipes containing saffron ingredient
    saffron_foods = conn.execute(text("""
        SELECT DISTINCT ri.food_item_id
        FROM recipe_ingredients ri
        JOIN ingredients ing ON ing.id = ri.ingredient_id
        WHERE LOWER(ing.name) LIKE '%saffron%'
    """)).fetchall()

    print(f"Recipes containing saffron: {len(saffron_foods)}")
    for row in saffron_foods:
        fid = row[0]
        rows = conn.execute(text("""
            SELECT ing.calories_per_100g, ing.protein_per_100g, ing.carbs_per_100g,
                   ing.fat_per_100g, ing.fiber_per_100g, ri.quantity_g
            FROM recipe_ingredients ri
            JOIN ingredients ing ON ing.id = ri.ingredient_id
            WHERE ri.food_item_id = :fid
        """), {"fid": fid}).fetchall()

        total_ing = len(rows)
        covered = sum(1 for r in rows if r[0] is not None and r[1] is not None
                      and r[2] is not None and r[3] is not None)
        coverage = covered / total_ing if total_ing else 0

        if coverage >= 0.80:
            cal = sum((r[0] or 0) * r[5] / 100 for r in rows)
            pro = sum((r[1] or 0) * r[5] / 100 for r in rows)
            crb = sum((r[2] or 0) * r[5] / 100 for r in rows)
            fat = sum((r[3] or 0) * r[5] / 100 for r in rows)
            fib = sum((r[4] or 0) * r[5] / 100 for r in rows)

            if 50 <= cal <= 1500:
                conn.execute(text("""
                    UPDATE food_items
                    SET cal_per_serving=:cal, protein_per_serving=:pro,
                        carbs_per_serving=:crb, fat_per_serving=:fat,
                        fiber_per_serving=:fib, nutrition_source='calculated'
                    WHERE id=:fid
                """), {"cal":round(cal,2),"pro":round(pro,2),"crb":round(crb,2),
                       "fat":round(fat,2),"fib":round(fib,2),"fid":fid})
                print(f"  ID={fid} recalculated: cal={cal:.0f} (now in valid range)")
            else:
                print(f"  ID={fid} still outlier after saffron fix: cal={cal:.0f} → left as manual")

print("\nTask 4A complete.")
