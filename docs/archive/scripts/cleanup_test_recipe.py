"""Delete test recipe ID 3723 created during second regression check."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://admin:mityahar_dev@localhost:5432/mityahar_db"

async def main():
    engine = create_async_engine(DATABASE_URL)
    async with engine.begin() as conn:
        r = await conn.execute(text(
            "DELETE FROM food_items WHERE id = 3723 AND recipe_name = 'Regression Test Dal'"
        ))
        print(f"Deleted {r.rowcount} test recipe(s)")
    await engine.dispose()

asyncio.run(main())
