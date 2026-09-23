"""TASK 2: Fix 18 beverage items with wrong slot_type → 'beverage'. Single transaction."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://admin:mityahar_dev@localhost:5432/mityahar_db"

BEVERAGE_IDS = [
    297,   # Buttermilk
    591,   # Buttermilk Soup
    1171,  # Espresso Coffee
    1177,  # Cinnamon Spiced Black Lemon Tea
    1179,  # Cinnamon Spiced Tea
    1209,  # Apple Tea Latte
    1216,  # Apple Tea Latte
    1218,  # Masala Chai
    1350,  # Adrak Chai
    1351,  # Adrak Chai
    1476,  # Ginger Lemon Black Tea
    1754,  # Ginger Tea
    1778,  # Filter Coffee
    2114,  # Turmeric Milk
    2196,  # Curry Leaves Buttermilk
    2447,  # Spiced Beetroot Buttermilk
    2616,  # Gulkand Chai
    3502,  # Kumbakonam Filter Coffee
]

async def main():
    engine = create_async_engine(DATABASE_URL)

    async with engine.begin() as conn:
        try:
            # Verify all IDs exist and show current state before updating
            placeholders = ", ".join(f":id{i}" for i in range(len(BEVERAGE_IDS)))
            params = {f"id{i}": v for i, v in enumerate(BEVERAGE_IDS)}
            result = await conn.execute(
                text(f"SELECT id, recipe_name, slot_type FROM food_items WHERE id IN ({placeholders}) ORDER BY id"),
                params
            )
            rows = result.fetchall()

            if len(rows) != len(BEVERAGE_IDS):
                found_ids = {r[0] for r in rows}
                missing = set(BEVERAGE_IDS) - found_ids
                raise ValueError(f"Missing food_item IDs: {missing}")

            print("Pre-fix state:")
            for row in rows:
                print(f"  ID {row[0]}: '{row[1]}' | slot_type='{row[2]}'")

            # Apply fix
            result2 = await conn.execute(
                text(f"UPDATE food_items SET slot_type = 'beverage' WHERE id IN ({placeholders})"),
                params
            )
            print(f"\nRows updated: {result2.rowcount}")

        except Exception as e:
            print(f"\nERROR — rolling back: {e}")
            raise

    print("Transaction committed.\n")

    # Verify
    async with engine.connect() as conn:
        placeholders = ", ".join(f":id{i}" for i in range(len(BEVERAGE_IDS)))
        params = {f"id{i}": v for i, v in enumerate(BEVERAGE_IDS)}
        result = await conn.execute(
            text(f"SELECT id, recipe_name, slot_type FROM food_items WHERE id IN ({placeholders}) ORDER BY id"),
            params
        )
        rows = result.fetchall()
        wrong = [r for r in rows if r[2] != 'beverage']
        print("=== VERIFICATION ===")
        print(f"All 18 items now slot_type='beverage': {'PASS' if not wrong else 'FAIL'}")
        if wrong:
            for r in wrong:
                print(f"  STILL WRONG: ID {r[0]} '{r[1]}' = '{r[2]}'")

        # Total beverage count
        total = await conn.execute(text("SELECT COUNT(*) FROM food_items WHERE slot_type = 'beverage'"))
        print(f"Total beverage items in DB now: {total.scalar()}")

    await engine.dispose()

asyncio.run(main())
