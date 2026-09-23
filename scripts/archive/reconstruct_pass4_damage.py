"""
One-off: reconstruct the ~383 rows corrupted by fix_ingredient_quantities.py's
Pass 4 (flat 180g cap for any quantity_g > 250, ignoring category).

Recovers the true pre-Pass4 value by:
  1. Reading the original quantity_g from db-backups/mityahar_content_2026-07-31.sql
     (confirmed pre-remediation: 628 rows > 250g, only 43 organically at 180g).
  2. Re-applying Pass 3's proportional dish-scaling formula ONLY for dishes whose
     backup total exceeded 800g (so we reconstruct the value Pass 4 actually saw,
     not the raw un-scaled original).
  3. Capping the reconstructed value to that ingredient's CATEGORY max_g (from
     sanity_check_ingredients.py's evidence-based rules) -- not a flat number.
  4. Leaving `quantity_g_corrected` BLANK for uncategorized ingredients -- no
     rule basis to auto-correct those, they need a human's eyes.

Writes corrections into data/review/recipe_ingredients_review.csv's quantity_g_corrected
column, in place, for every row whose current DB value is exactly 180.0 (the
Pass-4 fingerprint). Nothing else in the CSV is touched.

Usage:
    python -m scripts.reconstruct_pass4_damage
"""

import csv
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.sanity_check_ingredients import categorize_ingredient

BACKUP_SQL = PROJECT_ROOT / "db-backups" / "mityahar_content_2026-07-31.sql"
REVIEW_CSV = PROJECT_ROOT / "data" / "review" / "recipe_ingredients_review.csv"


def load_backup() -> dict[int, tuple[int, int, float]]:
    """ri_id -> (food_item_id, ingredient_id, quantity_g) from the pre-remediation dump."""
    with BACKUP_SQL.open(encoding="utf-8") as f:
        lines = f.readlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("COPY public.recipe_ingredients"))
    backup = {}
    for l in lines[start + 1:]:
        row = l.rstrip("\n")
        if row == "\\.":
            break
        parts = row.split("\t")
        ri_id, food_item_id, ingredient_id, qty = int(parts[0]), int(parts[1]), int(parts[2]), float(parts[3])
        backup[ri_id] = (food_item_id, ingredient_id, qty)
    return backup


def main():
    backup = load_backup()
    print(f"Loaded {len(backup):,} rows from pre-remediation backup (2026-07-31).")

    # backup dish totals, for re-deriving Pass 3's scale factor
    dish_totals: dict[int, float] = defaultdict(float)
    for _, (food_item_id, _, qty) in backup.items():
        dish_totals[food_item_id] += qty

    rows = list(csv.DictReader(open(REVIEW_CSV, encoding="utf-8-sig")))
    fieldnames = list(rows[0].keys())

    # Pass-4 fingerprint: current value is exactly 180.0
    damaged_ri_ids = {r["ri_id"] for r in rows if r["quantity_g"] == "180.0"}
    print(f"Rows currently at 180.0g (Pass-4 fingerprint): {len(damaged_ri_ids)}")

    corrections: dict[str, float] = {}
    uncategorized: list[str] = []

    for ri_id in damaged_ri_ids:
        ri_id_int = int(ri_id)
        if ri_id_int not in backup:
            continue  # row didn't exist pre-remediation (shouldn't happen, but be safe)
        food_item_id, ingredient_id, backup_qty = backup[ri_id_int]

        sample_row = next(r for r in rows if r["ri_id"] == ri_id)
        slot_type = sample_row["slot_type"]
        ingredient_name = sample_row["ingredient_name"]

        dish_backup_total = dish_totals[food_item_id]
        if dish_backup_total > 800.0:
            target_total = 400.0 if slot_type in ("beverage", "condiment", "accompaniment") else 450.0
            scale = target_total / dish_backup_total
            reconstructed = backup_qty * scale
        else:
            reconstructed = backup_qty

        rule = categorize_ingredient(ingredient_name)
        if rule is None:
            uncategorized.append(ri_id)
            continue

        corrected = min(reconstructed, rule.max_g)
        corrections[ri_id] = round(corrected, 1)

    print(f"Corrections computed (category-capped, evidence-based): {len(corrections)}")
    print(f"Left BLANK for manual review (uncategorized ingredient): {len(uncategorized)}")

    for r in rows:
        if r["ri_id"] in corrections:
            r["quantity_g_corrected"] = str(corrections[r["ri_id"]])

    with REVIEW_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote corrections into {REVIEW_CSV}")
    if uncategorized:
        print("\nUncategorized rows needing manual quantity_g_corrected (ri_id):")
        for ri_id in uncategorized:
            r = next(r for r in rows if r["ri_id"] == ri_id)
            print(f"  ri_id={ri_id:>6}  {r['dish_name'][:35]:35s} | {r['ingredient_name']}")


if __name__ == "__main__":
    main()
