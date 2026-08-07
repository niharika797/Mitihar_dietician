"""
For the dishes stuck under 50 kcal/serving, recover what the original ingest
silently dropped.

Root cause (scripts/seed_recipe_ingredients.py:68-70): any ingredient name
that didn't exact-match `ingredients.name_normalized` was skipped with a bare
`continue` -- no row, no flag, nothing persisted. `food_items.ingredients`
JSONB was never touched by that script though, so the original names
(including the ones that failed) are still sitting there. This re-runs the
same lookup against the ingredients table as it exists today (907 rows,
post-dedup -- bigger and cleaner than at original ingest time) to see which
of those names would now match.

Read-only: reports only, inserts nothing. A --write follow-up (matching the
populate_ingredient_nutrition.py convention) can insert the recoverable rows
once the report's been eyeballed.

Usage:
    python -m scripts.find_dropped_recipe_ingredients
"""
import asyncio
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from sqlalchemy import text
from app.core.database import AsyncSessionLocal

KCAL_THRESHOLD = 50
OUT_CSV = PROJECT_ROOT / "data" / "review" / "dropped_recipe_ingredients.csv"


def normalize(name: str) -> str:
    return re.sub(r'\s+', ' ', name.strip().lower())


async def fetch() -> tuple[list, int, int, int]:
    async with AsyncSessionLocal() as db:
        norm_to_id = dict((await db.execute(text(
            "SELECT name_normalized, id FROM ingredients WHERE name_normalized IS NOT NULL"
        ))).fetchall())

        low_kcal = (await db.execute(text("""
            SELECT id, recipe_name, cal_per_serving, ingredients
            FROM food_items
            WHERE cal_per_serving < :threshold
            ORDER BY cal_per_serving
        """), {"threshold": KCAL_THRESHOLD})).fetchall()

        linked = dict((await db.execute(text("""
            SELECT food_item_id, COUNT(*)
            FROM recipe_ingredients
            WHERE food_item_id = ANY(:ids)
            GROUP BY food_item_id
        """), {"ids": [r[0] for r in low_kcal]})).fetchall())

    rows = []
    now_recoverable = still_missing = 0
    for food_id, name, kcal, ingredients_json in low_kcal:
        for ing in (ingredients_json or []):
            ing_name = ing.get("name", "")
            amount_g = ing.get("amount_g")
            if not ing_name or amount_g is None:
                continue
            norm = normalize(ing_name)
            ing_id = norm_to_id.get(norm)
            status = "would_now_match" if ing_id else "still_unmatched"
            if ing_id:
                now_recoverable += 1
            else:
                still_missing += 1
            rows.append({
                "food_item_id": food_id, "recipe_name": name, "cal_per_serving": kcal,
                "linked_ingredient_rows": linked.get(food_id, 0),
                "ingredient_name": ing_name, "amount_g": amount_g,
                "status": status, "matched_ingredient_id": ing_id or "",
            })

    return rows, len(low_kcal), now_recoverable, still_missing


def main() -> None:
    rows, dish_count, now_recoverable, still_missing = asyncio.run(fetch())

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else [
            "food_item_id", "recipe_name", "cal_per_serving", "linked_ingredient_rows",
            "ingredient_name", "amount_g", "status", "matched_ingredient_id"])
        w.writeheader()
        w.writerows(rows)

    by_dish = defaultdict(list)
    for r in rows:
        by_dish[r["food_item_id"]].append(r)
    true_gaps = [fid for fid, items in by_dish.items()
                 if items[0]["linked_ingredient_rows"] < len(items)]

    print(f"{dish_count} dishes under {KCAL_THRESHOLD} kcal/serving")
    print(f"{now_recoverable} ingredient refs would now match (re-linkable today)")
    print(f"{still_missing} ingredient refs still unmatched (need a new ingredients row or synonym)")
    print(f"{len(true_gaps)}/{len(by_dish)} dishes actually have fewer recipe_ingredients rows "
          f"than JSONB ingredients (a real linkage gap): {true_gaps}")
    print("the rest are already fully linked -- low kcal there is a small-portion dish "
          "(condiment/garnish/dressing), not a data bug")
    print(f"-> {OUT_CSV}")


if __name__ == "__main__":
    main()
