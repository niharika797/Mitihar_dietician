"""Audit chai/coffee/tea/milk items with wrong slot_type."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://admin:mityahar_dev@localhost:5432/mityahar_db"

async def main():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        # What slot_type values exist?
        print("=== All distinct slot_type values in food_items ===")
        result = await conn.execute(text("""
            SELECT slot_type, COUNT(*) as count
            FROM food_items
            GROUP BY slot_type
            ORDER BY count DESC
        """))
        for row in result:
            print(f"  '{row[0]}': {row[1]} recipes")

        # Find chai/coffee/tea/milk items NOT in a beverage slot_type
        print("\n=== chai/coffee/tea/milk items with non-Beverage slot_type ===")
        result2 = await conn.execute(text("""
            SELECT id, recipe_name, slot_type
            FROM food_items
            WHERE recipe_name ILIKE '%chai%'
               OR recipe_name ILIKE '%coffee%'
               OR recipe_name ILIKE '%tea%'
               OR recipe_name ILIKE '%milk%'
            ORDER BY slot_type, recipe_name
        """))
        rows = result2.fetchall()
        print(f"Total chai/coffee/tea/milk items: {len(rows)}")
        print()

        wrong_slot = []
        for row in rows:
            fid, fname, fslot = row
            is_beverage = fslot is not None and fslot.lower() in ('beverage', 'beverages')
            marker = "OK" if is_beverage else "WRONG"
            print(f"  [{marker}] ID {fid} | '{fname}' | slot_type='{fslot}'")
            if not is_beverage:
                wrong_slot.append(row)

        print(f"\nItems needing slot_type fix: {len(wrong_slot)}")
        for row in wrong_slot:
            print(f"  ID {row[0]}: '{row[1]}' — current slot_type='{row[2]}'")

    await engine.dispose()

asyncio.run(main())
