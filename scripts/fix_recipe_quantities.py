"""
Recipe quantity fix pipeline — fixes 553 bad-quantity_g recipes.

Passes:
  A — Delete parsing artifact ingredient rows from recipe_ingredients
  B — Divide quantity_g by 10 for 551 inflated recipes
  C — Fix Makhana Pakora (ids 1990, 1995) — delete Gm artifact rows
  D — Recalculate all macros from corrected quantity_g for all fixed recipes
  E — Flip is_verified=True for recipes landing in 50-1500 kcal range
  F — Final report

Rollback:
  quantity_g: restore from db-backups/mityahar_2026-06-24.sql
  recipe names: UPDATE food_items SET recipe_name = original_name WHERE original_name IS NOT NULL

Run: python -m scripts.fix_recipe_quantities
"""

import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import text
from app.core.database import AsyncSessionLocal


MAKHANA_IDS = [1990, 1995]

ARTIFACT_WHERE = (
    "name LIKE 'To %' "
    "OR name LIKE '/ 2%' "
    "OR name LIKE '3/4 %' "
    "OR name LIKE '2 tsp%' "
    "OR name LIKE 'Gm %' "
    "OR name = 'Yield'"
)


async def snapshot_bad_set(db):
    result = await db.execute(text("""
        SELECT id, recipe_name, cal_per_serving, slot_type
        FROM food_items
        WHERE source = '6k_dataset'
          AND is_verified = FALSE
          AND nutrition_source = 'manual'
          AND cal_per_serving > 1500
        ORDER BY id
    """))
    return result.fetchall()


async def pass_a(db, bad_ids):
    result = await db.execute(text(f"""
        DELETE FROM recipe_ingredients
        WHERE food_item_id = ANY(:ids)
          AND ingredient_id IN (
              SELECT id FROM ingredients WHERE {ARTIFACT_WHERE}
          )
    """), {"ids": bad_ids})
    count = result.rowcount
    await db.commit()
    print(f"Pass A: {count} artifact ingredient rows deleted")
    return count


async def pass_b(db, bad_ids):
    non_makhana = [i for i in bad_ids if i not in MAKHANA_IDS]
    result = await db.execute(text("""
        UPDATE recipe_ingredients
        SET quantity_g = quantity_g / 10
        WHERE food_item_id = ANY(:ids)
    """), {"ids": non_makhana})
    count = result.rowcount
    await db.commit()
    print(f"Pass B: {count} ingredient rows divided by 10 ({len(non_makhana)} recipes)")
    return count


async def pass_c(db):
    result = await db.execute(text("""
        DELETE FROM recipe_ingredients
        WHERE food_item_id = ANY(:ids)
          AND ingredient_id IN (
              SELECT id FROM ingredients WHERE name LIKE 'Gm %'
          )
    """), {"ids": MAKHANA_IDS})
    count = result.rowcount
    await db.commit()
    print(f"Pass C: {count} Makhana Pakora artifact rows deleted")
    return count


async def pass_d(db, bad_ids):
    print(f"Pass D: recalculating nutrition for {len(bad_ids)} recipes...")
    new_cals = {}
    for i, food_id in enumerate(bad_ids, 1):
        result = await db.execute(text("""
            SELECT
                COALESCE(SUM(ri.quantity_g * i.calories_per_100g / 100), 0) AS cal,
                COALESCE(SUM(ri.quantity_g * i.protein_per_100g  / 100), 0) AS protein,
                COALESCE(SUM(ri.quantity_g * i.carbs_per_100g    / 100), 0) AS carbs,
                COALESCE(SUM(ri.quantity_g * i.fat_per_100g      / 100), 0) AS fat,
                COALESCE(SUM(ri.quantity_g * i.fiber_per_100g    / 100), 0) AS fiber,
                COALESCE(SUM(ri.quantity_g * i.sodium_per_100g   / 100), 0) AS sodium
            FROM recipe_ingredients ri
            JOIN ingredients i ON i.id = ri.ingredient_id
            WHERE ri.food_item_id = :fid
        """), {"fid": food_id})
        row = result.fetchone()
        await db.execute(text("""
            UPDATE food_items
            SET cal_per_serving     = :cal,
                protein_per_serving = :protein,
                carbs_per_serving   = :carbs,
                fat_per_serving     = :fat,
                fiber_per_serving   = :fiber,
                sodium_per_serving  = :sodium
            WHERE id = :fid
        """), {
            "cal": row.cal, "protein": row.protein, "carbs": row.carbs,
            "fat": row.fat, "fiber": row.fiber, "sodium": row.sodium,
            "fid": food_id,
        })
        new_cals[food_id] = float(row.cal)
        if i % 50 == 0:
            print(f"  {i}/{len(bad_ids)} recalculated...")
    await db.commit()
    print(f"Pass D: done — {len(bad_ids)} recipes recalculated")
    return new_cals


async def pass_e(db, bad_ids, new_cals):
    verified = []
    flagged = []
    for food_id in bad_ids:
        cal = new_cals[food_id]
        if 50 <= cal <= 1500:
            await db.execute(text(
                "UPDATE food_items SET is_verified = TRUE WHERE id = :id"
            ), {"id": food_id})
            verified.append(food_id)
        else:
            flagged.append((food_id, cal))
    await db.commit()
    print(f"Pass E: {len(verified)} verified, {len(flagged)} still flagged")
    if flagged:
        print("  Flagged (cal outside 50-1500 after fix):")
        for fid, cal in flagged:
            print(f"    id={fid}  cal={cal:.1f}")
    return verified, flagged


async def pass_f(db, snapshot, new_cals, verified_ids):
    total_verified_result = await db.execute(text(
        "SELECT count(*) FROM food_items WHERE is_verified = TRUE"
    ))
    total_verified = total_verified_result.scalar()

    print()
    print("=" * 64)
    print("Pass F: Final Report")
    print("=" * 64)
    print(f"  Recipes processed      : {len(snapshot)}")
    print(f"  Successfully verified  : {len(verified_ids)}")
    print(f"  Still flagged          : {len(snapshot) - len(verified_ids)}")
    print(f"  Total verified pool now: {total_verified}")
    print()
    print("  Sample of 10 fixed recipes:")
    print(f"  {'ID':>6}  {'Old kcal':>8}  {'New kcal':>8}  {'Slot':<12}  Name")
    print(f"  {'-'*6}  {'-'*8}  {'-'*8}  {'-'*12}  {'-'*30}")
    for row in snapshot[:10]:
        new_cal = new_cals.get(row.id, 0.0)
        print(
            f"  {row.id:>6}  {float(row.cal_per_serving):>8.0f}  "
            f"{new_cal:>8.0f}  {str(row.slot_type):<12}  {row.recipe_name[:40]}"
        )
    return total_verified


async def main():
    async with AsyncSessionLocal() as db:
        print("Snapshotting bad recipe set...")
        snapshot = await snapshot_bad_set(db)
        bad_ids = [r.id for r in snapshot]
        print(f"Found {len(bad_ids)} bad recipes (cal_per_serving > 1500, manual, unverified)")
        print()

        await pass_a(db, bad_ids)
        await pass_b(db, bad_ids)
        await pass_c(db)
        new_cals = await pass_d(db, bad_ids)
        verified_ids, _ = await pass_e(db, bad_ids, new_cals)
        await pass_f(db, snapshot, new_cals, verified_ids)


if __name__ == "__main__":
    asyncio.run(main())
