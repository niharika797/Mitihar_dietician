"""Investigate root cause of top outlier recipes."""
import os, sys
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))
from dotenv import load_dotenv; load_dotenv()
from sqlalchemy import create_engine, text

engine = create_engine(os.environ["DATABASE_URL"].replace("+asyncpg", "+psycopg2"))

SAMPLE_IDS = [1995, 420, 3336, 1339, 2618, 2567]  # worst outliers, sample

with engine.connect() as conn:
    for fid in SAMPLE_IDS:
        recipe = conn.execute(text(
            "SELECT recipe_name, cal_per_serving FROM food_items WHERE id=:fid"
        ), {"fid": fid}).fetchone()
        print(f"\n=== ID={fid} | {recipe[0]} | calc_cal={float(recipe[1]):.0f} ===")

        rows = conn.execute(text("""
            SELECT ing.name, ri.quantity_g, ing.calories_per_100g,
                   (ing.calories_per_100g * ri.quantity_g / 100) AS contribution
            FROM recipe_ingredients ri
            JOIN ingredients ing ON ing.id = ri.ingredient_id
            WHERE ri.food_item_id = :fid
            ORDER BY contribution DESC NULLS LAST
        """), {"fid": fid}).fetchall()

        for r in rows:
            contrib = float(r[3]) if r[3] else 0
            flag = " <<< HIGH qty" if float(r[1]) > 500 else ""
            print(f"  {str(r[0])[:35]:35} qty={float(r[1]):7.1f}g  cal/100g={float(r[2]) if r[2] else 'NULL':6}  contrib={contrib:8.1f} kcal{flag}")

    # Also check Green Chutney (low outlier)
    fid = 187
    recipe = conn.execute(text("SELECT recipe_name, cal_per_serving FROM food_items WHERE id=:fid"), {"fid": fid}).fetchone()
    print(f"\n=== ID={fid} | {recipe[0]} | calc_cal={float(recipe[1]):.0f} (below 50) ===")
    rows = conn.execute(text("""
        SELECT ing.name, ri.quantity_g, ing.calories_per_100g
        FROM recipe_ingredients ri JOIN ingredients ing ON ing.id=ri.ingredient_id
        WHERE ri.food_item_id=:fid
    """), {"fid": fid}).fetchall()
    for r in rows:
        print(f"  {str(r[0])[:35]:35} qty={float(r[1]):.1f}g  cal/100g={float(r[2]) if r[2] else 'NULL'}")

    # Summary: what's the typical quantity_g for outliers vs normal recipes?
    print("\n=== Quantity distribution ===")
    stats = conn.execute(text("""
        SELECT
            CASE WHEN fi.cal_per_serving > 1500 THEN 'outlier' ELSE 'normal' END AS grp,
            AVG(ri.quantity_g) AS avg_qty,
            MAX(ri.quantity_g) AS max_qty,
            COUNT(*) AS cnt
        FROM recipe_ingredients ri
        JOIN food_items fi ON fi.id = ri.food_item_id
        WHERE fi.nutrition_source = 'calculated'
        GROUP BY 1
    """)).fetchall()
    for r in stats:
        print(f"  {r[0]}: avg_qty={float(r[1]):.1f}g  max_qty={float(r[2]):.1f}g  rows={r[3]}")
