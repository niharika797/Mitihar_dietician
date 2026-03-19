"""
tag_pantry_staples.py
─────────────────────
Upgrade 3A — Tags every ingredient in food_items.ingredients JSONB
with "is_pantry_staple": true/false based on a hardcoded set of
common Indian kitchen staples.

Usage:
    venv\\Scripts\\python scripts\\tag_pantry_staples.py
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://admin:mityahar_dev@localhost:5432/mityahar_db",
).replace("+asyncpg", "+psycopg2")

# ── Pantry-staple names (case-insensitive match) ─────────────────────────────
PANTRY_STAPLES = {
    "salt", "oil", "ghee", "butter", "sugar", "water",
    "turmeric", "cumin", "coriander", "mustard seeds",
    "hing", "asafoetida", "curry leaves", "bay leaf",
    "cloves", "cardamom", "cinnamon", "pepper",
    "chilli powder", "red chilli", "green chilli",
    "ginger", "garlic", "ginger garlic paste", "oil spray",
}

BATCH_SIZE = 100


def main():
    engine = create_engine(DATABASE_URL)
    total_staples = 0
    total_recipes = 0
    batch = []

    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT id, ingredients FROM food_items WHERE ingredients != '[]'")
        ).fetchall()

        total_recipes = len(rows)
        print(f"Processing {total_recipes} recipes...")

        for idx, (fid, ingredients) in enumerate(rows, 1):
            # Parse JSONB (may already be a list if driver handles it)
            if isinstance(ingredients, str):
                ings = json.loads(ingredients)
            else:
                ings = ingredients

            changed = False
            for ing in ings:
                is_staple = ing.get("name", "").strip().lower() in PANTRY_STAPLES
                if ing.get("is_pantry_staple") != is_staple:
                    changed = True
                ing["is_pantry_staple"] = is_staple
                if is_staple:
                    total_staples += 1

            if changed:
                batch.append((json.dumps(ings), fid))

            # Flush batch
            if len(batch) >= BATCH_SIZE:
                _flush_batch(conn, batch)
                batch.clear()

            if idx % 200 == 0:
                print(f"  ... processed {idx}/{total_recipes} rows")

        # Final flush
        if batch:
            _flush_batch(conn, batch)
            batch.clear()

        conn.commit()

    print(f"\nTagged {total_staples} pantry staples across {total_recipes} recipes.")


def _flush_batch(conn, batch):
    for ingredients_json, fid in batch:
        conn.execute(
            text("UPDATE food_items SET ingredients = CAST(:ings AS jsonb) WHERE id = :id"),
            {"ings": ingredients_json, "id": fid},
        )


if __name__ == "__main__":
    main()
