"""Check what slot_types appear in meal templates stored in DB."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://admin:mityahar_dev@localhost:5432/mityahar_db"

async def main():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT DISTINCT mt.meal_time, mt.diet_type,
                   slot->>'slot_type' AS slot_type
            FROM meal_templates mt, jsonb_array_elements(mt.slots) AS slot
            ORDER BY mt.meal_time, slot->>'slot_type'
        """))
        rows = result.fetchall()
        print("Slot types used in meal_templates:")
        for row in rows:
            print(f"  meal_time={row[0]}, diet={row[1]}, slot_type={row[2]}")

        # Does any template use 'beverage' as a slot_type?
        bev_result = await conn.execute(text("""
            SELECT COUNT(*) FROM meal_templates, jsonb_array_elements(slots) AS slot
            WHERE slot->>'slot_type' = 'beverage'
        """))
        bev_count = bev_result.scalar()
        print(f"\nTemplates with slot_type='beverage': {bev_count}")

    await engine.dispose()

asyncio.run(main())
