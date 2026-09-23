"""Investigate why 197 recipes are already is_verified=TRUE."""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://admin:mityahar_dev@localhost:5432/mityahar_db"

async def main():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        # Distribution by source
        print("=== Verified recipes by source ===")
        r = await conn.execute(text("""
            SELECT source, COUNT(*) FROM food_items
            WHERE is_verified = TRUE GROUP BY source ORDER BY COUNT(*) DESC
        """))
        for row in r:
            print(f"  source='{row[0]}': {row[1]}")

        # Distribution of ALL recipes by source (for comparison)
        print("\n=== All recipes by source ===")
        r2 = await conn.execute(text("""
            SELECT source, is_verified, COUNT(*) FROM food_items
            GROUP BY source, is_verified ORDER BY source, is_verified
        """))
        for row in r2:
            print(f"  source='{row[0]}', is_verified={row[1]}: {row[2]}")

        # Sample 5 verified recipes
        print("\n=== Sample 5 verified recipes ===")
        r3 = await conn.execute(text("""
            SELECT id, recipe_name, source, doctor_id, created_at
            FROM food_items WHERE is_verified = TRUE
            ORDER BY id LIMIT 5
        """))
        for row in r3:
            print(f"  ID {row[0]}: '{row[1]}' | source={row[2]} | doctor_id={row[3]} | created={row[4]}")

        # Check if doctor-submitted recipes are verified
        print("\n=== Doctor-submitted recipes (doctor_id IS NOT NULL) ===")
        r4 = await conn.execute(text("""
            SELECT is_verified, COUNT(*) FROM food_items
            WHERE doctor_id IS NOT NULL GROUP BY is_verified
        """))
        for row in r4:
            print(f"  doctor_id IS NOT NULL, is_verified={row[0]}: {row[1]}")

        # Alembic migration history — when was is_verified added?
        print("\n=== Alembic version history ===")
        r5 = await conn.execute(text("SELECT version_num FROM alembic_version"))
        for row in r5:
            print(f"  Current migration: {row[0]}")

    await engine.dispose()

asyncio.run(main())
