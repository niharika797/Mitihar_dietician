"""TASK 3: Verify is_verified column exists and has correct defaults."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://admin:mityahar_dev@localhost:5432/mityahar_db"

async def main():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        # Check column definition
        result = await conn.execute(text("""
            SELECT column_name, data_type, column_default, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'food_items' AND column_name = 'is_verified'
        """))
        row = result.fetchone()
        if row:
            print(f"Column: {row[0]}, type={row[1]}, default={row[2]}, nullable={row[3]}")
        else:
            print("ERROR: is_verified column NOT FOUND")
            return

        # Count verified vs unverified
        r1 = await conn.execute(text("SELECT COUNT(*) FROM food_items WHERE is_verified = TRUE"))
        r2 = await conn.execute(text("SELECT COUNT(*) FROM food_items WHERE is_verified = FALSE"))
        r3 = await conn.execute(text("SELECT COUNT(*) FROM food_items"))
        verified = r1.scalar()
        unverified = r2.scalar()
        total = r3.scalar()

        print(f"Total food_items: {total}")
        print(f"is_verified=TRUE:  {verified}")
        print(f"is_verified=FALSE: {unverified}")
        print(f"Sum matches total: {verified + unverified == total}")

        if verified == 0 and unverified == total:
            print("PASS — all existing recipes default to unverified (correct)")
        else:
            print(f"NOTE — {verified} recipes already marked verified")

    await engine.dispose()

asyncio.run(main())
