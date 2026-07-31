"""
Stage 6 Section 0 duplicate-dish audit — READ-ONLY, no writes.

Reproduces the method documented in docs/DISH_DUPLICATE_AUDIT.md:
  - group food_items by normalized recipe_name (lower, strip, collapse whitespace)
  - Tier 1 (exact duplicate): within a group, all 7 macro fields equal
    (cal/protein/carbs/fat/fiber/sodium_per_serving, serving_weight_g) AND
    recipe_ingredients sets equal as (ingredient_id, quantity_g) pairs
  - Tier 2 (conflict): same normalized name, any macro or ingredient difference

Runs against whatever DATABASE_URL points at (local dev or staging Cloud Run job).
"""
import os
import re
from collections import defaultdict

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import create_engine, text

DATABASE_URL = os.environ["DATABASE_URL"].replace("+asyncpg", "+psycopg2")
engine = create_engine(DATABASE_URL)

TEST_ARTIFACT_NAMES = {"doctor2 private dal", "global test recipe", "to be rejected recipe"}


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def main() -> None:
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT id, recipe_name, slot_type, diet_type, is_verified, source, "
            "cal_per_serving, protein_per_serving, carbs_per_serving, fat_per_serving, "
            "fiber_per_serving, sodium_per_serving, serving_weight_g "
            "FROM food_items ORDER BY id"
        )).fetchall()
        ri = conn.execute(text(
            "SELECT food_item_id, ingredient_id, quantity_g FROM recipe_ingredients"
        )).fetchall()

    ing_by_food = defaultdict(set)
    for food_id, ing_id, qty in ri:
        ing_by_food[food_id].add((ing_id, qty))

    groups = defaultdict(list)
    for r in rows:
        groups[norm(r.recipe_name)].append(r)

    dup_groups = {name: g for name, g in groups.items() if len(g) > 1}
    tier1, tier2 = {}, {}
    for name, g in dup_groups.items():
        sig = lambda r: (r.cal_per_serving, r.protein_per_serving, r.carbs_per_serving,
                         r.fat_per_serving, r.fiber_per_serving, r.sodium_per_serving,
                         r.serving_weight_g, frozenset(ing_by_food[r.id]))
        (tier1 if len({sig(r) for r in g}) == 1 else tier2)[name] = g

    t1_rows = sum(len(g) for g in tier1.values())
    t2_rows = sum(len(g) for g in tier2.values())
    print(f"Total food_items rows:      {len(rows)}")
    print(f"Distinct normalized names:  {len(groups)}")
    print(f"Duplicate groups (>1 row):  {len(dup_groups)} ({sum(len(g) for g in dup_groups.values())} rows)")
    print(f"Tier 1 exact duplicates:    {len(tier1)} groups, {t1_rows} rows -> {t1_rows - len(tier1)} removable")
    print(f"Tier 2 conflicting:         {len(tier2)} groups, {t2_rows} rows")

    diet_variant = {n: g for n, g in tier1.items() if len({r.diet_type for r in g}) > 1}
    print(f"\nTier 1 diet-variant groups (excluded from merge): {len(diet_variant)}")
    for n, g in sorted(diet_variant.items()):
        print(f"  {n}: " + ", ".join(f"{r.id} {r.slot_type}/{r.diet_type}" for r in g))

    artifacts = [r for n, g in groups.items() if n in TEST_ARTIFACT_NAMES for r in g]
    print(f"\nTest-artifact rows present: {len(artifacts)}")
    for r in sorted(artifacts, key=lambda r: r.id):
        print(f"  {r.id} {r.recipe_name!r} source={r.source} verified={r.is_verified}")

    # verified-pool cross-check against the prior 284 figure (name+slot_type, is_verified only)
    vgroups = defaultdict(list)
    for r in rows:
        if r.is_verified:
            vgroups[(norm(r.recipe_name), r.slot_type)].append(r)
    vdups = {k: g for k, g in vgroups.items() if len(g) > 1}
    print(f"\nVerified pool name+slot dup groups: {len(vdups)} ({sum(len(g) for g in vdups.values())} rows)")


if __name__ == "__main__":
    main()
