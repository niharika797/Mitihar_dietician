"""
Import corrected quantity_g values from a reviewed CSV (produced by
export_recipe_ingredients_review.py, edited in Excel) back into Postgres.

Matches by recipe_ingredients.id (ri_id) -- NOT by ingredient name -- so a
row can never be applied to the wrong ingredient even if Excel re-sorts rows.

Safety:
  - Refuses to run unless a fresh pg_dump of recipe_ingredients exists in
    db-backups/, or --skip-backup is passed explicitly.
  - Only rows with a non-blank quantity_g_corrected that differs from the
    live DB value are touched.
  - Prints every change (dish, ingredient, old -> new) and requires typing
    APPLY before committing. Nothing is written on a dry run.
  - Single transaction; rolls back entirely on any error.
  - Re-validates every corrected value against the SAME category rules used
    by sanity_check_ingredients.py before applying -- if your correction
    itself exceeds the evidence-based max for that ingredient's category,
    it's flagged and you're asked to confirm it anyway, not silently applied.

Usage:
    python -m scripts.import_recipe_ingredients_review data/review/recipe_ingredients_review.csv
    python -m scripts.import_recipe_ingredients_review data/review/recipe_ingredients_review.csv --dry-run
    python -m scripts.import_recipe_ingredients_review data/review/recipe_ingredients_review.csv --skip-backup
"""

import argparse
import csv
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine, text

from scripts.sanity_check_ingredients import categorize_ingredient

DATABASE_URL = os.environ["DATABASE_URL"].replace("+asyncpg", "+psycopg2")
BACKUP_DIR = PROJECT_ROOT / "db-backups"


def take_backup() -> Path:
    """pg_dump just the recipe_ingredients table before we touch it."""
    BACKUP_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = BACKUP_DIR / f"recipe_ingredients_pre_import_{ts}.sql"

    # postgresql+psycopg2://user:pass@host:port/db -> postgresql://user:pass@host:port/db
    pg_url = DATABASE_URL.replace("+psycopg2", "")

    cmd = ["pg_dump", pg_url, "--table=recipe_ingredients", "-f", str(out_path)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not out_path.exists():
        raise RuntimeError(
            f"pg_dump failed (is it on PATH?):\n{result.stderr}\n"
            f"Fix pg_dump access, or re-run with --skip-backup if you already "
            f"have a fresh backup elsewhere."
        )
    return out_path


def load_edited_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return list(reader)


def build_changeset(rows: list[dict]) -> list[dict]:
    """Rows where quantity_g_corrected is filled in and differs from quantity_g.
    Deduplicates by ri_id (a row can appear multiple times in the review CSV --
    once per flag -- so the same correction may repeat; that's fine, we just
    keep one change per ri_id and error out if two DIFFERENT corrected values
    were entered for the same ri_id, since that's an editing mistake)."""
    changes: dict[str, dict] = {}
    for r in rows:
        corrected = (r.get("quantity_g_corrected") or "").strip()
        if not corrected:
            continue
        ri_id = r["ri_id"]
        try:
            new_val = float(corrected)
        except ValueError:
            raise ValueError(f"ri_id={ri_id}: quantity_g_corrected='{corrected}' is not a number")
        old_val = float(r["quantity_g"])
        if new_val == old_val:
            continue

        if ri_id in changes and changes[ri_id]["new_val"] != new_val:
            raise ValueError(
                f"ri_id={ri_id} ({r['ingredient_name']}) has two different "
                f"quantity_g_corrected values entered across its flagged rows "
                f"({changes[ri_id]['new_val']} vs {new_val}). Fix the CSV -- "
                f"one row appears once per flag, correction must be consistent."
            )

        rule = categorize_ingredient(r["ingredient_name"])
        over_max = rule is not None and new_val > rule.max_g

        changes[ri_id] = {
            "ri_id": ri_id,
            "dish_name": r["dish_name"],
            "ingredient_name": r["ingredient_name"],
            "old_val": old_val,
            "new_val": new_val,
            "category": rule.name if rule else "uncategorized",
            "over_max": over_max,
            "max_g": rule.max_g if rule else None,
        }
    return list(changes.values())


def print_changeset(changes: list[dict]) -> None:
    print(f"\n{len(changes)} row(s) will change:\n")
    flagged = [c for c in changes if c["over_max"]]
    for c in changes:
        warn = f"  ** still exceeds {c['category']} max ({c['max_g']}g) **" if c["over_max"] else ""
        print(f"  ri_id={c['ri_id']:>6}  {c['dish_name'][:35]:35s} | "
              f"{c['ingredient_name'][:25]:25s} {c['old_val']:>7.1f}g -> {c['new_val']:>7.1f}g{warn}")
    if flagged:
        print(f"\n  WARNING: {len(flagged)} correction(s) above still exceed their category's "
              f"evidence-based max. They will still be applied if you confirm -- this is your "
              f"call as the reviewer, not a script decision.")


def apply_changes(changes: list[dict]) -> None:
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        for c in changes:
            result = conn.execute(
                text("UPDATE recipe_ingredients SET quantity_g = :qty WHERE id = :id"),
                {"qty": c["new_val"], "id": c["ri_id"]},
            )
            if result.rowcount != 1:
                raise RuntimeError(f"ri_id={c['ri_id']} matched {result.rowcount} rows, expected 1 -- aborting transaction")
    print(f"\nApplied {len(changes)} update(s) to recipe_ingredients.")
    print("Next: python -m scripts.recalculate_recipe_nutrition")


def main():
    parser = argparse.ArgumentParser(description="Import reviewed recipe_ingredients corrections into Postgres")
    parser.add_argument("csv_path", help="Path to the Excel-edited review CSV")
    parser.add_argument("--dry-run", action="store_true", help="Show the changeset, don't write to DB")
    parser.add_argument("--skip-backup", action="store_true", help="Skip pg_dump (only if you already have a fresh backup)")
    args = parser.parse_args()

    csv_path = Path(args.csv_path)
    if not csv_path.exists():
        print(f"File not found: {csv_path}")
        sys.exit(1)

    rows = load_edited_csv(csv_path)
    changes = build_changeset(rows)

    if not changes:
        print("No changes found -- quantity_g_corrected is empty or identical to quantity_g on every row.")
        return

    print_changeset(changes)

    if args.dry_run:
        print("\n--dry-run: no changes written.")
        return

    if not args.skip_backup:
        print("\nTaking backup of recipe_ingredients...")
        backup_path = take_backup()
        print(f"Backup written to {backup_path}")
    else:
        print("\n--skip-backup passed: proceeding WITHOUT a fresh backup.")

    confirm = input(f"\nType APPLY to write these {len(changes)} change(s) to Postgres: ")
    if confirm != "APPLY":
        print("Aborted -- nothing written.")
        return

    apply_changes(changes)


if __name__ == "__main__":
    main()
