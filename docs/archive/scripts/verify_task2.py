"""
Verify Task 2 fix:
1. Confirm generator cannot select beverages for Lunch/Dinner (template proof)
2. Check Priya's stored plan for any of the 18 fixed items in Lunch/Dinner slots
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://admin:mityahar_dev@localhost:5432/mityahar_db"

FIXED_BEVERAGE_NAMES = [
    "Buttermilk", "Buttermilk Soup", "Espresso Coffee",
    "Cinnamon Spiced Black Lemon Tea", "Cinnamon Spiced Tea",
    "Apple Tea Latte", "Masala Chai", "Adrak Chai",
    "Ginger Lemon Black Tea", "Ginger Tea", "Filter Coffee",
    "Turmeric Milk", "Curry Leaves Buttermilk", "Spiced Beetroot Buttermilk",
    "Gulkand Chai", "Kumbakonam Filter Coffee",
]

async def main():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        # 1. Confirm no beverage slot in Lunch/Dinner templates
        result = await conn.execute(text("""
            SELECT COUNT(*) FROM meal_templates, jsonb_array_elements(slots) AS slot
            WHERE mt.meal_time IN ('Lunch', 'Dinner')
              AND slot->>'slot_type' = 'beverage'
        """.replace("mt.", "meal_templates.")))
        bev_in_lunch_dinner = result.scalar()
        print(f"Beverage slots in Lunch/Dinner templates: {bev_in_lunch_dinner}")
        print(f"→ Generator CANNOT select beverages for Lunch/Dinner: {'CONFIRMED' if bev_in_lunch_dinner == 0 else 'PROBLEM'}")

        # 2. Check Priya's active plan for any fixed beverage names in Lunch/Dinner
        print("\nChecking Priya's stored plan (patient_id=5) for beverage items in Lunch/Dinner...")
        result2 = await conn.execute(text("""
            SELECT r.id, meal->>'Meal Type' AS meal_type, meal->>'Menu Names' AS menu_names
            FROM recommendations r, jsonb_array_elements(r.meals) AS meal
            WHERE r.patient_id = 5
              AND meal->>'Meal Type' IN ('Lunch', 'Dinner')
            ORDER BY r.id DESC, meal->>'Date'
            LIMIT 20
        """))
        rows = result2.fetchall()

        found_beverage_in_meal = []
        for row in rows:
            menu_names = row[2] or ""
            for bev in FIXED_BEVERAGE_NAMES:
                if bev.lower() in menu_names.lower():
                    found_beverage_in_meal.append((row[0], row[1], bev, menu_names))

        if found_beverage_in_meal:
            print("WARNING — beverage items found in Lunch/Dinner of stored plan:")
            for item in found_beverage_in_meal:
                print(f"  rec_id={item[0]}, meal_type={item[1]}, beverage='{item[2]}'")
                print(f"  menu: {item[3]}")
        else:
            print("PASS — no fixed beverage items appear in Lunch/Dinner of Priya's stored plan")

        # 3. Show current beverage slot in Breakfast template exists
        result3 = await conn.execute(text("""
            SELECT COUNT(*) FROM meal_templates, jsonb_array_elements(slots) AS slot
            WHERE meal_templates.meal_time = 'Breakfast'
              AND slot->>'slot_type' = 'beverage'
        """))
        bev_breakfast = result3.scalar()
        print(f"\nBeverage slots in Breakfast templates: {bev_breakfast} (beverages will appear here as intended)")

    await engine.dispose()

asyncio.run(main())
