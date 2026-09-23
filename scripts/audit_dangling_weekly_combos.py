"""
Find weekly_combos rows whose embedded dish references (dishes[].food_id in
the JSONB) point at a soft-deleted or missing food_items row.

Reproduces last session's "1,388 refs / 1 dangling id (3718)" figures with
current numbers -- they'll have moved since the dedup pass. READ-ONLY, no
writes. Confirmed safe by construction: weekly_combos.dishes is a
self-contained JSONB snapshot (name/kcal/macros baked in at generation time),
so a dangling food_id doesn't break display -- app/services/meal_generator
and app/services/diet_plan_service.py never re-join combos back to
food_items to render them. This script only counts/reports; deciding whether
to backfill the pre-existing dangling rows is a separate call.

Usage:
    python -m scripts.audit_dangling_weekly_combos
"""
import csv
import os
from collections import Counter
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

from sqlalchemy import create_engine, text

DATABASE_URL = os.environ["DATABASE_URL"].replace("+asyncpg", "+psycopg2")
engine = create_engine(DATABASE_URL)
OUT_CSV = PROJECT_ROOT / "data" / "review" / "dangling_weekly_combos.csv"


def main() -> None:
    with engine.connect() as conn:
        food_status = dict(conn.execute(text(
            "SELECT id, deleted_at IS NOT NULL FROM food_items"
        )).fetchall())

        combos = conn.execute(text(
            "SELECT id, recommendation_id, slot_date, meal_type, dishes FROM weekly_combos"
        )).fetchall()

    total_refs = dangling_refs = 0
    missing_food_ids: Counter = Counter()   # referenced id has no food_items row at all
    soft_deleted_refs = 0
    rows = []

    for combo_id, rec_id, slot_date, meal_type, dishes in combos:
        for d in (dishes or []):
            food_id = d.get("food_id")
            if food_id is None:
                continue
            total_refs += 1
            if food_id not in food_status:
                missing_food_ids[food_id] += 1
                dangling_refs += 1
                rows.append({"combo_id": combo_id, "recommendation_id": rec_id,
                             "slot_date": slot_date, "meal_type": meal_type,
                             "food_id": food_id, "reason": "missing"})
            elif food_status[food_id]:
                soft_deleted_refs += 1
                dangling_refs += 1
                rows.append({"combo_id": combo_id, "recommendation_id": rec_id,
                             "slot_date": slot_date, "meal_type": meal_type,
                             "food_id": food_id, "reason": "soft_deleted"})

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["combo_id", "recommendation_id", "slot_date",
                                           "meal_type", "food_id", "reason"])
        w.writeheader()
        w.writerows(rows)

    print(f"{len(combos)} weekly_combos rows, {total_refs} total dish refs")
    print(f"{dangling_refs} dangling refs: {soft_deleted_refs} soft-deleted dish, "
          f"{len(missing_food_ids)} distinct missing food_id(s) "
          f"({sum(missing_food_ids.values())} refs) -- {sorted(missing_food_ids)}")
    print(f"-> {OUT_CSV}")


if __name__ == "__main__":
    main()
