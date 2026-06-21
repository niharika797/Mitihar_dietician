"""
Layer 3 — derive food_items.avoid_tags / prefer_tags from ingredient-level tags.

For each food_item that has recipe_ingredients:
  avoid_tags: propagate if ANY ingredient with that tag has qty >= AVOID_MIN_G[tag]
  prefer_tags: propagate if sum(qty of tagged ingredients) / total_weight >= PREFER_FRAC[tag]
  gluten_free (special): only if NO ingredient with avoid_gluten is present at >= 5g

Thresholds are conservative intentionally — tune AVOID_MIN_G / PREFER_FRAC if needed.
Run is idempotent: clears and rewrites avoid_tags/prefer_tags on every run.
"""
import asyncio
import json
from collections import defaultdict

import asyncpg

DSN = "postgresql://admin:mityahar_dev@localhost:5432/mityahar_db"

# Minimum grams of a triggering ingredient to propagate an avoid_tag to the recipe.
AVOID_MIN_G: dict[str, float] = {
    "avoid_gluten":      5.0,   # celiac — any meaningful amount matters
    "avoid_ibs":         5.0,   # FODMAP triggers active at low dose
    "avoid_diabetes":   10.0,
    "avoid_fattyliver": 10.0,
    "avoid_hypertension":10.0,
    "avoid_gout":       10.0,
    "avoid_highchol":   10.0,
    "avoid_heart":      10.0,
    "avoid_kidney":     10.0,
    "avoid_hypothyroid":10.0,
    "avoid_hyperthyroid":10.0,
    "avoid_pcos":       10.0,
}

# Weight fraction (0–1) threshold for prefer_tags.
# gluten_free handled separately.
PREFER_FRAC: dict[str, float] = {
    "iron_rich":          0.15,
    "calcium_rich":       0.15,
    "thyroid_support":    0.20,
    "liver_friendly":     0.30,
    "pcos_friendly":      0.30,
    "diabetes_friendly":  0.40,
    "cholesterol_friendly":0.40,
    "heart_friendly":     0.40,
    "gut_friendly":       0.40,
}

GLUTEN_MIN_G = 5.0   # qty threshold for gluten_free eligibility check


def parse_tags(raw) -> list[str]:
    if isinstance(raw, list):
        return list(raw)
    if isinstance(raw, str):
        return json.loads(raw)
    return []


def derive_tags(
    ingredients: list[tuple[list[str], list[str], float]],  # (avoid, prefer, qty_g)
) -> tuple[list[str], list[str]]:
    """Return (avoid_tags, prefer_tags) for a recipe given its ingredient tag/qty list."""
    total_weight = sum(qty for _, _, qty in ingredients if qty > 0)

    # ── avoid_tags ────────────────────────────────────────────────────────────
    new_avoid: set[str] = set()
    for avoid, _, qty in ingredients:
        if qty <= 0:
            continue
        for tag in avoid:
            threshold = AVOID_MIN_G.get(tag, 10.0)
            if qty >= threshold:
                new_avoid.add(tag)

    # ── prefer_tags ───────────────────────────────────────────────────────────
    new_prefer: set[str] = set()

    # gluten_free: special — no avoid_gluten ingredient at >= GLUTEN_MIN_G
    has_gluten_ingredient = any(
        "avoid_gluten" in avoid and qty >= GLUTEN_MIN_G
        for avoid, _, qty in ingredients
        if qty > 0
    )
    if not has_gluten_ingredient and total_weight > 0:
        new_prefer.add("gluten_free")

    # weight-fraction prefer tags
    if total_weight > 0:
        tag_weight: dict[str, float] = defaultdict(float)
        for _, prefer, qty in ingredients:
            if qty <= 0:
                continue
            for tag in prefer:
                tag_weight[tag] += qty

        for tag, frac in PREFER_FRAC.items():
            if tag_weight.get(tag, 0) / total_weight >= frac:
                new_prefer.add(tag)

    return sorted(new_avoid), sorted(new_prefer)


async def main() -> None:
    conn = await asyncpg.connect(DSN)

    print("=== Layer 3 — derive_recipe_tags ===\n")

    # Load all ingredient tags into memory keyed by ingredient_id
    ing_rows = await conn.fetch(
        "SELECT id, avoid_tags, prefer_tags FROM ingredients"
    )
    ing_tags: dict[int, tuple[list[str], list[str]]] = {}
    for r in ing_rows:
        ing_tags[r["id"]] = (
            parse_tags(r["avoid_tags"]),
            parse_tags(r["prefer_tags"]),
        )
    print(f"Loaded tags for {len(ing_tags)} ingredients")
    tagged_count = sum(1 for a, p in ing_tags.values() if a or p)
    print(f"  {tagged_count} have at least one tag")

    # Load all recipe_ingredients
    ri_rows = await conn.fetch(
        "SELECT food_item_id, ingredient_id, quantity_g FROM recipe_ingredients"
    )
    # Group by food_item_id
    food_ings: dict[int, list[tuple[list[str], list[str], float]]] = defaultdict(list)
    for r in ri_rows:
        fid = r["food_item_id"]
        iid = r["ingredient_id"]
        qty = r["quantity_g"] or 0.0
        avoid, prefer = ing_tags.get(iid, ([], []))
        food_ings[fid].append((avoid, prefer, qty))

    print(f"Loaded {len(ri_rows)} recipe_ingredient links across {len(food_ings)} food_items\n")

    # Derive tags for each food_item
    updates: list[tuple[str, str, int]] = []   # (avoid_json, prefer_json, food_item_id)
    avoid_dist: dict[str, int] = defaultdict(int)
    prefer_dist: dict[str, int] = defaultdict(int)

    all_fids = await conn.fetch("SELECT id FROM food_items")
    for row in all_fids:
        fid = row["id"]
        ings = food_ings.get(fid, [])
        if not ings:
            # No recipe_ingredients — write empty tags
            updates.append(("[]", "[]", fid))
            continue
        avoid, prefer = derive_tags(ings)
        for t in avoid:
            avoid_dist[t] += 1
        for t in prefer:
            prefer_dist[t] += 1
        updates.append((json.dumps(avoid), json.dumps(prefer), fid))

    # Bulk update in a transaction
    print(f"Writing tags to {len(updates)} food_items...")
    async with conn.transaction():
        await conn.executemany(
            "UPDATE food_items SET avoid_tags=$1::jsonb, prefer_tags=$2::jsonb WHERE id=$3",
            updates,
        )

    # ── Summary ───────────────────────────────────────────────────────────────
    any_tagged = sum(1 for a, p, _ in updates if a != "[]" or p != "[]")
    print(f"Done. {any_tagged}/{len(updates)} food_items received at least one tag.\n")

    print("avoid_tag distribution (recipes tagged):")
    for tag, count in sorted(avoid_dist.items(), key=lambda x: -x[1]):
        print(f"  {tag}: {count}")

    print("\nprefer_tag distribution (recipes tagged):")
    for tag, count in sorted(prefer_dist.items(), key=lambda x: -x[1]):
        print(f"  {tag}: {count}")

    # ── Spot-checks ───────────────────────────────────────────────────────────
    print("\n── Spot-checks ──")

    # Ragi-based recipe should have gluten_free + iron_rich
    ragi_fi = await conn.fetchrow(
        """SELECT fi.id, fi.recipe_name, fi.avoid_tags, fi.prefer_tags
           FROM food_items fi
           JOIN recipe_ingredients ri ON ri.food_item_id = fi.id
           JOIN ingredients i ON i.id = ri.ingredient_id
           WHERE LOWER(i.name) = 'ragi flour' AND ri.quantity_g >= 30
           LIMIT 1"""
    )
    if ragi_fi:
        prefer = parse_tags(ragi_fi["prefer_tags"])
        print(f"Ragi recipe '{ragi_fi['recipe_name']}': "
              f"gluten_free={'gluten_free' in prefer} iron_rich={'iron_rich' in prefer}")
        print(f"  prefer={prefer}")
    else:
        print("  WARN: no ragi_flour recipe found for spot-check")

    # Wheat-based recipe should have avoid_gluten, NOT gluten_free
    wheat_fi = await conn.fetchrow(
        """SELECT fi.id, fi.recipe_name, fi.avoid_tags, fi.prefer_tags
           FROM food_items fi
           JOIN recipe_ingredients ri ON ri.food_item_id = fi.id
           JOIN ingredients i ON i.id = ri.ingredient_id
           WHERE LOWER(i.name) LIKE '%wheat flour%' AND ri.quantity_g >= 10
           LIMIT 1"""
    )
    if wheat_fi:
        avoid = parse_tags(wheat_fi["avoid_tags"])
        prefer = parse_tags(wheat_fi["prefer_tags"])
        print(f"Wheat recipe '{wheat_fi['recipe_name']}': "
              f"avoid_gluten={'avoid_gluten' in avoid} gluten_free={'gluten_free' in prefer}")
    else:
        print("  WARN: no wheat_flour recipe found for spot-check")

    # Dal-heavy recipe should have diabetes_friendly
    dal_fi = await conn.fetchrow(
        """SELECT fi.id, fi.recipe_name, fi.avoid_tags, fi.prefer_tags
           FROM food_items fi
           JOIN recipe_ingredients ri ON ri.food_item_id = fi.id
           JOIN ingredients i ON i.id = ri.ingredient_id
           WHERE LOWER(i.name) LIKE '%dal%' AND ri.quantity_g >= 60
           LIMIT 1"""
    )
    if dal_fi:
        prefer = parse_tags(dal_fi["prefer_tags"])
        print(f"Dal recipe '{dal_fi['recipe_name']}': "
              f"diabetes_friendly={'diabetes_friendly' in prefer}")
        print(f"  prefer={prefer}")
    else:
        print("  WARN: no dal recipe found for spot-check")

    # Jaggery recipe should have avoid_diabetes
    jag_fi = await conn.fetchrow(
        """SELECT fi.id, fi.recipe_name, fi.avoid_tags, fi.prefer_tags
           FROM food_items fi
           JOIN recipe_ingredients ri ON ri.food_item_id = fi.id
           JOIN ingredients i ON i.id = ri.ingredient_id
           WHERE LOWER(i.name) = 'jaggery' AND ri.quantity_g >= 10
           LIMIT 1"""
    )
    if jag_fi:
        avoid = parse_tags(jag_fi["avoid_tags"])
        print(f"Jaggery recipe '{jag_fi['recipe_name']}': "
              f"avoid_diabetes={'avoid_diabetes' in avoid}")
    else:
        print("  WARN: no jaggery recipe found for spot-check")

    await conn.close()
    print("\nLayer 3 complete.")


asyncio.run(main())
