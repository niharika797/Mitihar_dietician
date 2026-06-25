"""
Task 5 — Link food_items JSONB ingredients to recipe_ingredients table.

For each food_item with JSONB ingredients, match each ingredient name
to ingredients table by name_normalized, then insert recipe_ingredients row.
Runs idempotently (DELETE + INSERT per food_item).
Prints match rate.
"""
import asyncio
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import text
from app.core.database import AsyncSessionLocal


def normalize(name: str) -> str:
    return re.sub(r'\s+', ' ', name.strip().lower())


async def main() -> None:
    async with AsyncSessionLocal() as db:
        # Build name_normalized → id lookup for ingredients
        result = await db.execute(text(
            "SELECT id, name_normalized FROM ingredients WHERE name_normalized IS NOT NULL"
        ))
        norm_to_id: dict[str, int] = {row[1]: row[0] for row in result.fetchall()}
        print(f"Ingredients in lookup: {len(norm_to_id)}")

        # Fetch all food_items with non-empty JSONB ingredients
        result = await db.execute(text("""
            SELECT id, jsonb_array_length(ingredients), ingredients
            FROM food_items
            WHERE jsonb_array_length(ingredients) > 0
            ORDER BY id
        """))
        food_items = result.fetchall()
        print(f"Food items to process: {len(food_items)}")

        total_refs = 0
        matched_refs = 0
        unmatched_names: set[str] = set()

        for food_id, _, ingredients_json in food_items:
            if not ingredients_json:
                continue

            # Delete existing recipe_ingredients for this food_item (idempotent)
            await db.execute(text(
                "DELETE FROM recipe_ingredients WHERE food_item_id = :fid"
            ), {"fid": food_id})

            for ing in ingredients_json:
                name = ing.get("name", "")
                amount_g = ing.get("amount_g")
                if not name or amount_g is None:
                    continue

                if not amount_g or float(amount_g) <= 0:
                    continue
                total_refs += 1
                norm = normalize(name)
                ing_id = norm_to_id.get(norm)

                if ing_id is None:
                    unmatched_names.add(name)
                    continue

                await db.execute(text("""
                    INSERT INTO recipe_ingredients (food_item_id, ingredient_id, quantity_g)
                    VALUES (:fid, :iid, :qty)
                """), {"fid": food_id, "iid": ing_id, "qty": float(amount_g)})
                matched_refs += 1

        await db.commit()

        match_pct = round(matched_refs * 100 / total_refs, 1) if total_refs else 0
        print(f"\nTotal ingredient references: {total_refs}")
        print(f"Matched:   {matched_refs} ({match_pct}%)")
        print(f"Unmatched: {total_refs - matched_refs} ({round(100 - match_pct, 1)}%)")

        # Verify row count
        count = await db.execute(text("SELECT COUNT(*) FROM recipe_ingredients"))
        print(f"\nrecipe_ingredients rows inserted: {count.scalar()}")

        if unmatched_names:
            print(f"\nSample unmatched names ({min(20, len(unmatched_names))} of {len(unmatched_names)}):")
            for n in sorted(unmatched_names)[:20]:
                print(f"  - {n}")


if __name__ == "__main__":
    asyncio.run(main())
