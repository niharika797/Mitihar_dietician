"""Read raw recommendations.meals JSONB for patient_id=5, show 2 meal slots."""
import asyncio
import json
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://admin:mityahar_dev@localhost:5432/mityahar_db"

async def main():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        r = await conn.execute(text("""
            SELECT id, week_start_date, jsonb_array_length(meals) as slot_count,
                   meals->0 as first_meal,
                   meals->1 as second_meal
            FROM recommendations
            WHERE patient_id = 5
            ORDER BY id DESC
            LIMIT 1
        """))
        row = r.fetchone()
        if not row:
            print("No recommendations found for patient_id=5")
            return

        print(f"Recommendation ID: {row[0]}, week_start: {row[1]}, total slots: {row[2]}")
        print("\n--- First meal slot (raw JSONB) ---")
        print(json.dumps(row[3], indent=2, ensure_ascii=False))
        print("\n--- Second meal slot (raw JSONB) ---")
        print(json.dumps(row[4], indent=2, ensure_ascii=False))

        # Also show all unique keys across all meal slots
        r2 = await conn.execute(text("""
            SELECT DISTINCT jsonb_object_keys(meal)
            FROM recommendations, jsonb_array_elements(meals) AS meal
            WHERE patient_id = 5
            ORDER BY 1
        """))
        keys = [row[0] for row in r2]
        print(f"\nAll keys present across meal slots: {keys}")

    await engine.dispose()

asyncio.run(main())
