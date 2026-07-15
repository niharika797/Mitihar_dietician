"""Audit food_items schema then find items with ingredient amounts > 10,000g."""
import asyncio
import json
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://admin:mityahar_dev@localhost:5432/mityahar_db"

async def main():
    engine = create_async_engine(DATABASE_URL)
    async with engine.connect() as conn:
        # First: check actual column names
        cols = await conn.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'food_items'
            ORDER BY ordinal_position
        """))
        print("food_items columns:")
        col_names = []
        for row in cols:
            print(f"  {row[0]}: {row[1]}")
            col_names.append(row[0])

        # Identify name-like column
        name_col = None
        for c in ['dish_name', 'name', 'recipe_name', 'food_name', 'title']:
            if c in col_names:
                name_col = c
                break
        print(f"\nUsing name column: {name_col}")

        if name_col is None:
            print("No name column found — check column list above")
            return

        # Find items with ingredient amounts > 10000
        result = await conn.execute(text(f"""
            SELECT
                fi.id,
                fi.{name_col},
                fi.ingredients
            FROM food_items fi
            WHERE fi.ingredients IS NOT NULL
              AND jsonb_typeof(fi.ingredients) = 'array'
              AND EXISTS (
                SELECT 1
                FROM jsonb_array_elements(fi.ingredients) AS ing
                WHERE (ing->>'amount_g') ~ '^[0-9.]+$'
                  AND (ing->>'amount_g')::numeric > 10000
            )
            ORDER BY fi.id
        """))
        rows = result.fetchall()

        print(f"\nFound {len(rows)} food_items with ingredient amount_g > 10,000g")
        print("=" * 80)

        for row in rows:
            fid, fname, ingredients = row
            print(f"\nID: {fid} | Name: {fname}")
            print("Raw JSONB:")
            print(json.dumps(ingredients, indent=2, ensure_ascii=False))
            print("\nOffending ingredients (amount_g > 10000):")
            for ing in ingredients:
                amt = ing.get('amount_g')
                if amt is not None:
                    try:
                        if float(amt) > 10000:
                            print(f"  - {ing.get('name', 'UNKNOWN')}: {amt}g")
                    except (ValueError, TypeError):
                        pass
            print("-" * 80)

    await engine.dispose()

asyncio.run(main())
