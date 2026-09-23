"""
Export recipe_ingredients to a REVIEW csv with a stable primary key (ri_id).

Unlike data/review/recipe_ingredients_audit.csv (name-matched, no PK -- cannot be safely
re-imported), this CSV carries recipe_ingredients.id per row. Edit the
`quantity_g_corrected` column in Excel; leave it blank to make no change.
The `severity`/`check`/`message`/`category` columns are computed by the SAME
logic as sanity_check_ingredients.py (imported, not re-derived), so this tool
and the checker can never disagree with each other.

Read-only. Output: data/review/recipe_ingredients_review.csv.

Usage:
    python -m scripts.export_recipe_ingredients_review
"""

import asyncio
import csv
import sys
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.db_models import FoodItem, Ingredient, RecipeIngredient
from scripts.sanity_check_ingredients import run_checks, safe_float

OUTPUT = PROJECT_ROOT / "data" / "review" / "recipe_ingredients_review.csv"

FIELDNAMES = [
    "ri_id", "food_item_id", "ingredient_id",
    "dish_name", "slot_type", "is_verified",
    "ingredient_name", "quantity_g",
    "category", "severity", "check", "message",
    "suggested_g",
    "dish_total_g", "dish_total_flag",
    "quantity_g_corrected",   # <-- edit this column in Excel; blank = no change
]


async def fetch_rows() -> list[dict]:
    stmt = (
        select(
            RecipeIngredient.id.label("ri_id"),
            FoodItem.id.label("dish_id"),
            FoodItem.recipe_name.label("dish_name"),
            FoodItem.slot_type,
            FoodItem.is_verified,
            Ingredient.id.label("ingredient_id"),
            Ingredient.name.label("ingredient_name"),
            RecipeIngredient.quantity_g,
        )
        .join(FoodItem, FoodItem.id == RecipeIngredient.food_item_id)
        .join(Ingredient, Ingredient.id == RecipeIngredient.ingredient_id)
        .order_by(FoodItem.id, RecipeIngredient.id)
    )
    async with AsyncSessionLocal() as session:
        result = await session.execute(stmt)
        rows = result.all()

    # Build the dict shape sanity_check_ingredients.run_checks() expects
    # (dish_id/ingredient_name/quantity_g/slot_type as strings), plus the
    # extra PK columns it doesn't care about and will just ignore.
    out = []
    for r in rows:
        out.append({
            "ri_id": r.ri_id,
            "dish_id": str(r.dish_id),
            "dish_name": r.dish_name,
            "slot_type": r.slot_type or "",
            "is_verified": str(r.is_verified),
            "ingredient_id": r.ingredient_id,
            "ingredient_name": r.ingredient_name,
            "quantity_g": str(float(r.quantity_g)),
        })
    return out


def main():
    rows = asyncio.run(fetch_rows())
    print(f"Loaded {len(rows):,} recipe_ingredients rows.")

    results, dish_flags = run_checks(rows)

    dish_flags_map = {}
    for dish_id, _, flags in dish_flags:
        dish_flags_map[dish_id] = flags

    # dish totals for the review column (same calc the checker uses internally)
    by_dish = defaultdict(list)
    for r in rows:
        by_dish[r["dish_id"]].append(r)
    dish_totals = {
        dish_id: sum(safe_float(r["quantity_g"]) for r in dish_rows)
        for dish_id, dish_rows in by_dish.items()
    }

    with OUTPUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()

        for res in results:
            row = res.row
            dish_flag_msgs = " | ".join(fl.message for fl in dish_flags_map.get(row["dish_id"], []))

            if res.flags:
                for flag in res.flags:
                    suggested = ""
                    if flag.check == "egg_count_not_grams":
                        suggested = str(safe_float(row["quantity_g"]) * 50)
                    writer.writerow({
                        "ri_id": row["ri_id"],
                        "food_item_id": row["dish_id"],
                        "ingredient_id": row["ingredient_id"],
                        "dish_name": row["dish_name"],
                        "slot_type": row["slot_type"],
                        "is_verified": row["is_verified"],
                        "ingredient_name": row["ingredient_name"],
                        "quantity_g": row["quantity_g"],
                        "category": res.category,
                        "severity": flag.severity,
                        "check": flag.check,
                        "message": flag.message,
                        "suggested_g": suggested,
                        "dish_total_g": round(dish_totals[row["dish_id"]], 1),
                        "dish_total_flag": dish_flag_msgs,
                        "quantity_g_corrected": "",
                    })
            else:
                writer.writerow({
                    "ri_id": row["ri_id"],
                    "food_item_id": row["dish_id"],
                    "ingredient_id": row["ingredient_id"],
                    "dish_name": row["dish_name"],
                    "slot_type": row["slot_type"],
                    "is_verified": row["is_verified"],
                    "ingredient_name": row["ingredient_name"],
                    "quantity_g": row["quantity_g"],
                    "category": res.category,
                    "severity": "OK",
                    "check": "",
                    "message": "",
                    "suggested_g": "",
                    "dish_total_g": round(dish_totals[row["dish_id"]], 1),
                    "dish_total_flag": dish_flag_msgs,
                    "quantity_g_corrected": "",
                })

    print(f"Wrote {len(rows):,} rows to {OUTPUT}")
    print("Open in Excel, fill quantity_g_corrected for rows you want changed, save as CSV.")
    print("Then run: python -m scripts.import_recipe_ingredients_review <path-to-edited-csv>")


if __name__ == "__main__":
    main()
