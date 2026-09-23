import argparse
import os
from sqlalchemy import create_engine
from sqlalchemy.sql import text

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="apply the fixes (default is dry-run preview)")
    args = ap.parse_args()

    DATABASE_URL = os.environ["DATABASE_URL"].replace("+asyncpg", "+psycopg2")
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        tag_count = conn.execute(text("""
            SELECT count(*) FROM food_items
            WHERE slot_type = 'snack_item'
              AND NOT ('Evening_Snack' = ANY(meal_time_tags))
        """)).scalar()
        print(f"Fix 1 would tag {tag_count} snack_item row(s) for the Evening_Snack pool")

        rows_to_delete = conn.execute(text("""
            SELECT id, recipe_name, cal_per_serving FROM food_items
            WHERE source = '6k_dataset' AND cal_per_serving < 30
        """)).fetchall()
        print(f"Fix 2 would delete {len(rows_to_delete)} near-zero-calorie row(s):")
        for r in rows_to_delete:
            print(f"  id={r.id} {r.recipe_name!r} cal={r.cal_per_serving}")

        if not args.write:
            print("\nDry run. Re-run with --write to apply.")
            return

        print("Executing Fix 1: Tagging existing snack_items for Evening_Snack pool")
        conn.execute(text("""
            UPDATE food_items
            SET meal_time_tags = array_append(meal_time_tags, 'Evening_Snack')
            WHERE slot_type = 'snack_item'
              AND NOT ('Evening_Snack' = ANY(meal_time_tags));
        """))

        print("Executing Fix 2: Deleting near-zero calorie rows from the earlier check")
        result = conn.execute(text("""
            DELETE FROM food_items
            WHERE source = '6k_dataset'
              AND cal_per_serving < 30;
        """))
        print(f"Rows deleted: {result.rowcount}")

    print("SQL fixes applied successfully.")

if __name__ == "__main__":
    main()
