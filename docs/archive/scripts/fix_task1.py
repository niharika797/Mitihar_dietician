"""
TASK 1 fix:
  1. Audit all 'Gm ' prefix ingredient names across all food_items (KNOWN ISSUES scope)
  2. Fix 6 corrupted records: amount_g → 150, clean name prefix
  3. Verify zero records with amount_g > 10,000 after fix
All DB writes in a single transaction — rollback on any error.
"""
import asyncio
import json
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DATABASE_URL = "postgresql+asyncpg://admin:mityahar_dev@localhost:5432/mityahar_db"

# Confirmed fixes: (food_item_id, old_ingredient_name, new_ingredient_name, new_amount_g)
FIXES = [
    (1317, "Gm small potatoes", "Small potatoes", 150.0),
    (1320, "Gm small potatoes", "Small potatoes", 150.0),
    (1718, "Gm arabic",         "Arbi (taro)",    150.0),
    (1726, "Gm parwal",         "Parwal (pointed gourd)", 150.0),
    (2924, "Gm arabic",         "Arbi (taro)",    150.0),
    (3128, "Gm arabic",         "Arbi (taro)",    150.0),
]

async def main():
    engine = create_async_engine(DATABASE_URL)

    # --- PHASE 1: Audit Gm-prefix names across ALL food_items (read-only) ---
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT DISTINCT ing->>'name' AS ing_name, COUNT(*) OVER (PARTITION BY ing->>'name') AS occurrences
            FROM food_items, jsonb_array_elements(ingredients) AS ing
            WHERE ing->>'name' ILIKE 'Gm %'
            ORDER BY ing_name
        """))
        gm_names = result.fetchall()

        print(f"=== Gm-prefix ingredient names across ALL food_items ===")
        print(f"Total distinct names with 'Gm ' prefix: {len(gm_names)}\n")
        for row in gm_names:
            print(f"  '{row[0]}' — appears in {row[1]} recipe(s)")

        # Also get total recipe count affected
        total_affected = await conn.execute(text("""
            SELECT COUNT(DISTINCT fi.id)
            FROM food_items fi, jsonb_array_elements(fi.ingredients) AS ing
            WHERE ing->>'name' ILIKE 'Gm %'
        """))
        total_count = total_affected.scalar()
        print(f"\nTotal food_items with at least one 'Gm ' ingredient name: {total_count}")

    print("\n" + "=" * 70)
    print("=== PHASE 2: Applying fixes in single transaction ===\n")

    # --- PHASE 2: Apply fixes in a single transaction ---
    async with engine.begin() as conn:
        try:
            for food_id, old_name, new_name, new_amount in FIXES:
                # Fetch current ingredients for this food_item
                row = await conn.execute(
                    text("SELECT ingredients FROM food_items WHERE id = :id FOR UPDATE"),
                    {"id": food_id}
                )
                result_row = row.fetchone()
                if result_row is None:
                    raise ValueError(f"food_item id={food_id} not found")

                ingredients = result_row[0]
                updated = False

                new_ingredients = []
                for ing in ingredients:
                    if ing.get('name') == old_name:
                        print(f"  ID {food_id}: '{old_name}' ({ing['amount_g']}g) → '{new_name}' (150g)")
                        new_ing = dict(ing)
                        new_ing['name'] = new_name
                        new_ing['amount_g'] = new_amount
                        new_ingredients.append(new_ing)
                        updated = True
                    else:
                        new_ingredients.append(ing)

                if not updated:
                    raise ValueError(f"food_item id={food_id}: ingredient '{old_name}' not found in JSONB")

                await conn.execute(
                    text("UPDATE food_items SET ingredients = CAST(:ing AS jsonb) WHERE id = :id"),
                    {"ing": json.dumps(new_ingredients, ensure_ascii=False), "id": food_id}
                )

            print("\nAll 6 records updated. Committing transaction...")
            # Transaction commits automatically on context exit

        except Exception as e:
            print(f"\nERROR — rolling back: {e}")
            raise

    print("Transaction committed.\n")

    # --- PHASE 3: Verify zero records with amount_g > 10,000 ---
    async with engine.connect() as conn:
        result = await conn.execute(text("""
            SELECT COUNT(*) FROM food_items
            WHERE ingredients IS NOT NULL
              AND jsonb_typeof(ingredients) = 'array'
              AND EXISTS (
                SELECT 1 FROM jsonb_array_elements(ingredients) AS ing
                WHERE (ing->>'amount_g') ~ '^[0-9.]+$'
                  AND (ing->>'amount_g')::numeric > 10000
              )
        """))
        remaining = result.scalar()
        print(f"=== VERIFICATION ===")
        print(f"Records with amount_g > 10,000g remaining: {remaining}")
        if remaining == 0:
            print("PASS — zero corrupted amounts remain.")
        else:
            print("FAIL — still have corrupted records, investigate.")

    await engine.dispose()

asyncio.run(main())
