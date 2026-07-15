"""Export all dishes + raw ingredient quantities to CSV for manual auditing.

Read-only. Output: recipe_ingredients_audit.csv in project root.

Usage:
    python -m scripts.export_recipes_to_csv
"""

import asyncio
import csv
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.db_models import FoodItem, Ingredient, RecipeIngredient

OUTPUT = Path(__file__).resolve().parent.parent / "recipe_ingredients_audit.csv"


async def main() -> None:
    stmt = (
        select(
            FoodItem.id.label("dish_id"),
            FoodItem.recipe_name.label("dish_name"),
            FoodItem.slot_type,
            FoodItem.is_verified,
            Ingredient.name.label("ingredient_name"),
            RecipeIngredient.quantity_g,
        )
        # outerjoin: dishes with no recipe_ingredients rows still appear (blank ingredient cols)
        .outerjoin(RecipeIngredient, RecipeIngredient.food_item_id == FoodItem.id)
        .outerjoin(Ingredient, Ingredient.id == RecipeIngredient.ingredient_id)
        .order_by(FoodItem.id)
    )

    async with AsyncSessionLocal() as session:
        result = await session.execute(stmt)
        rows = result.all()

    with OUTPUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["dish_id", "dish_name", "slot_type", "is_verified", "ingredient_name", "quantity_g"])
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUTPUT}")


if __name__ == "__main__":
    asyncio.run(main())
