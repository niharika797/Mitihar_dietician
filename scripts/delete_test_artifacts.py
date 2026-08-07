"""
Stage 6 Section 1: delete the 21 full_backend_test.py residue rows from
food_items (ids 3697-3717 — 'Doctor2 Private Dal' / 'Global Test Recipe' /
'To Be Rejected Recipe', 3 groups of 7, all is_verified=False).

Product-owner decision: delete outright, no soft-flag, no Tier 1 merge.

FK blast-radius trace (docs/DISH_DUPLICATE_AUDIT.md Section 0 method, run
2026-07-15 against local dev): zero references in meal_logs, doctor_meal_overrides
(rejected_food_id/chosen_food_id), meal_ratings, patient_dish_preferences,
patient_meal_choices, patient_meal_choice_dishes, or recommendations.meals JSONB.
Only recipe_ingredients.food_item_id references these ids (21 rows, ON DELETE
CASCADE) — junk ingredient rows for the dummy dishes, removed automatically.

Default is dry-run (prints what would be deleted). Run with --write to apply;
it will still ask for an explicit "Y".
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import create_engine, text

DATABASE_URL = os.environ["DATABASE_URL"].replace("+asyncpg", "+psycopg2")
engine = create_engine(DATABASE_URL)

TEST_ARTIFACT_IDS = list(range(3697, 3718))  # 3697..3717 inclusive, 21 ids

# Every table with a FK to food_items.id (app/models/db_models.py) that is
# NOT already ON DELETE CASCADE. These are checked so the script fails loudly
# if new data has appeared instead of silently violating a constraint.
BLOCKING_CHECKS = [
    ("meal_logs", "food_id"),
    ("doctor_meal_overrides", "rejected_food_id"),
    ("doctor_meal_overrides", "chosen_food_id"),
    ("meal_ratings", "food_item_id"),
    ("patient_meal_choice_dishes", "food_item_id"),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="apply delete (asks Y first)")
    args = ap.parse_args()

    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT id, recipe_name, source, is_verified FROM food_items "
            "WHERE id = ANY(:ids) ORDER BY id"
        ), {"ids": TEST_ARTIFACT_IDS}).fetchall()

        print(f"food_items rows matching the 21 test-artifact ids: {len(rows)}")
        for r in rows:
            print(f"  {r.id} {r.recipe_name!r} source={r.source} verified={r.is_verified}")

        ri_count = conn.execute(text(
            "SELECT count(*) FROM recipe_ingredients WHERE food_item_id = ANY(:ids)"
        ), {"ids": TEST_ARTIFACT_IDS}).scalar()
        print(f"\nrecipe_ingredients rows that will CASCADE-delete: {ri_count}")

        blocked = False
        for table, col in BLOCKING_CHECKS:
            n = conn.execute(text(
                f"SELECT count(*) FROM {table} WHERE {col} = ANY(:ids)"
            ), {"ids": TEST_ARTIFACT_IDS}).scalar()
            if n:
                blocked = True
                print(f"  BLOCKED: {table}.{col} has {n} referencing row(s) — delete will fail on FK constraint")

    if len(rows) != 21:
        print(f"\nExpected exactly 21 rows, found {len(rows)}. Aborting — verify the id range before proceeding.")
        return

    if blocked:
        print("\nReferencing rows found in a non-CASCADE table. Not safe to delete as-is. Aborting.")
        return

    if not args.write:
        print("\nDry-run only. Re-run with --write to apply.")
        return
    if input("\nDelete these 21 food_items rows (and their 21 CASCADE recipe_ingredients rows)? Type Y to confirm: ").strip() != "Y":
        print("Aborted.")
        return

    with engine.begin() as conn:
        result = conn.execute(text(
            "DELETE FROM food_items WHERE id = ANY(:ids)"
        ), {"ids": TEST_ARTIFACT_IDS})
        print(f"Deleted {result.rowcount} food_items rows.")


if __name__ == "__main__":
    main()
