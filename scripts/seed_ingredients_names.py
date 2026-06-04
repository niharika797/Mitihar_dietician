"""
Task 3 — Seed unique ingredient names from food_items.ingredients JSONB
into the ingredients master table.

Nutrition columns left NULL — filled in Task 4.
Runs idempotently (INSERT ... ON CONFLICT DO NOTHING on name).
"""
import asyncio
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import text
from app.core.database import AsyncSessionLocal


def normalize(name: str) -> str:
    return re.sub(r'\s+', ' ', name.strip().lower())


async def main() -> None:
    async with AsyncSessionLocal() as db:
        # Extract all unique ingredient names from JSONB
        result = await db.execute(text("""
            SELECT DISTINCT ing->>'name' AS name
            FROM food_items, jsonb_array_elements(ingredients) AS ing
            WHERE ing->>'name' IS NOT NULL
              AND trim(ing->>'name') != ''
            ORDER BY 1
        """))
        names = [row[0] for row in result.fetchall()]
        print(f"Unique ingredient names extracted: {len(names)}")

        inserted = 0
        skipped = 0
        for name in names:
            norm = normalize(name)
            r = await db.execute(text("""
                INSERT INTO ingredients (name, name_normalized, source, is_verified)
                VALUES (:name, :norm, 'pending', false)
                ON CONFLICT (name, source) DO NOTHING
                RETURNING id
            """), {"name": name, "norm": norm})
            if r.fetchone():
                inserted += 1
            else:
                skipped += 1

        await db.commit()
        print(f"Inserted: {inserted}  |  Skipped (already existed): {skipped}")

        # Verify
        total = await db.execute(text("SELECT COUNT(*) FROM ingredients"))
        print(f"Total rows in ingredients table: {total.scalar()}")


if __name__ == "__main__":
    asyncio.run(main())
