import os
from sqlalchemy import create_engine
from sqlalchemy.sql import text

def main():
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://admin:mityahar_dev@localhost:5432/mityahar_db")
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
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
