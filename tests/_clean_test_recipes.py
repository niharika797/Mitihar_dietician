import asyncio
from app.core.database import AsyncSessionLocal
from sqlalchemy import text

async def clean():
    async with AsyncSessionLocal() as s:
        result = await s.execute(
            text("SELECT id, is_verified FROM food_items WHERE recipe_name = :n"),
            {"n": "Test Dal Tadka"},
        )
        rows = result.fetchall()
        print(f"Found {len(rows)} Test Dal Tadka rows:", rows)
        if rows:
            ids = [r[0] for r in rows]
            await s.execute(
                text("DELETE FROM food_items WHERE id = ANY(:ids)"),
                {"ids": ids},
            )
            await s.commit()
            print("Deleted all")

asyncio.run(clean())
