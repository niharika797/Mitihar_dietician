import os, sys
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import create_engine, text

engine = create_engine(os.environ["DATABASE_URL"].replace("+asyncpg", "+psycopg2"))
with engine.connect() as conn:
    rows = conn.execute(text("""
        SELECT fi.id, fi.recipe_name, fi.cal_per_serving, fi.protein_per_serving,
               fi.carbs_per_serving, fi.fat_per_serving, fi.fiber_per_serving,
               COUNT(ri.id) AS ing_count,
               SUM(CASE WHEN ing.calories_per_100g IS NOT NULL THEN 1 ELSE 0 END) AS covered
        FROM food_items fi
        JOIN recipe_ingredients ri ON ri.food_item_id = fi.id
        JOIN ingredients ing ON ing.id = ri.ingredient_id
        WHERE fi.nutrition_source = 'calculated'
        GROUP BY fi.id, fi.recipe_name, fi.cal_per_serving, fi.protein_per_serving,
                 fi.carbs_per_serving, fi.fat_per_serving, fi.fiber_per_serving
        ORDER BY fi.id
        LIMIT 10
    """)).fetchall()

    print("--- 10 Calculated Recipes ---")
    for r in rows:
        cal = float(r[2])
        flag = " *** OUTLIER ***" if not (50 <= cal <= 1500) else ""
        coverage = int(r[8]) / int(r[7]) * 100 if r[7] else 0
        print(f"  ID={r[0]} | {str(r[1])[:45]}")
        print(f"    Cal={cal:.0f} Pro={float(r[3]):.1f}g Carb={float(r[4]):.1f}g "
              f"Fat={float(r[5]):.1f}g Fib={float(r[6]):.1f}g | "
              f"ings={r[7]} cov={coverage:.0f}%{flag}")
    print()

    out_rows = conn.execute(text("""
        SELECT id, recipe_name, cal_per_serving
        FROM food_items
        WHERE nutrition_source = 'calculated'
          AND (cal_per_serving < 50 OR cal_per_serving > 1500)
        ORDER BY cal_per_serving DESC
        LIMIT 30
    """)).fetchall()

    print(f"--- Outliers (cal outside 50-1500): {len(out_rows)} found ---")
    for r in out_rows:
        print(f"  ID={r[0]} cal={float(r[2]):.0f} | {str(r[1])[:65]}")
