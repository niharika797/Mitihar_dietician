"""
Stage 2 backfill: copy legacy food_items.ingredients JSONB entries into
recipe_ingredients for dishes where recipe_ingredients is missing data.

Direction is JSONB -> recipe_ingredients ONLY (JSONB is being retired).
Gram conflicts on shared ingredients are NOT touched here — all 5,759 of them
are exactly 10x stale pre-fix_recipe_quantities.py values; recipe_ingredients
is the corrected source (see docs/NUTRITION_SOURCE_MIGRATION.md).

Default is dry-run (prints proposed inserts, writes nothing).
Run with --write to apply; it will still ask for an explicit "Y".

Flags (never auto-written, listed for review):
  - entries with quantity <= 0 or missing (CHECK ck_ri_quantity_positive would reject)
  - entries with quantity > 1000g for a single ingredient (implausible, likely batch error)
  - measurement-phrase artifact names ("To 12 curry leaves", "/ 2 tablespoon oil") —
    same ARTIFACT_RE class import_ifct.py skips; backfilling them would inject the
    exact garbage Stage 3 cleans up
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import create_engine, text

DATABASE_URL = os.environ["DATABASE_URL"].replace("+asyncpg", "+psycopg2")
engine = create_engine(DATABASE_URL)

IMPLAUSIBLE_G = 1000.0

# Same artifact filter as scripts/import_ifct.py — measurement phrases baked into names.
ARTIFACT_RE = re.compile(
    r'^\s*[\d/]'
    r'|tablespoon|teaspoon|\btbsp\b|\btsp\b|\bcup\b|\bcups\b|\bml\b|\bkg\b'
    r'|\b(or|to)\s+\d',
    re.IGNORECASE,
)


def norm(s: str) -> str:
    return (s or "").strip().lower()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="apply inserts (asks Y first)")
    args = ap.parse_args()

    with engine.connect() as conn:
        fi_rows = conn.execute(text(
            "SELECT id, recipe_name, ingredients FROM food_items "
            "WHERE ingredients IS NOT NULL AND ingredients::text NOT IN ('[]', 'null') ORDER BY id"
        )).fetchall()
        ri_rows = conn.execute(text(
            "SELECT ri.food_item_id, ing.name FROM recipe_ingredients ri "
            "JOIN ingredients ing ON ing.id = ri.ingredient_id"
        )).fetchall()
        master = conn.execute(text(
            "SELECT id, name_normalized FROM ingredients"
        )).fetchall()

    ri_names: dict[int, set[str]] = {}
    for fid, name in ri_rows:
        ri_names.setdefault(fid, set()).add(norm(name))
    master_by_norm = {n: i for i, n in master}

    proposed = []   # (fid, dish, ing_name, grams, ingredient_id or None)
    flagged = []    # (fid, dish, ing_name, raw_value, reason)

    for fid, dish, j_list in fi_rows:
        if not isinstance(j_list, list):
            continue
        existing = ri_names.get(fid, set())
        for e in j_list:
            if not isinstance(e, dict):
                continue
            name = (e.get("name") or "").strip()
            if not name or norm(name) in existing:
                continue
            raw = e.get("amount_g", e.get("quantity"))
            if ARTIFACT_RE.search(name):
                flagged.append((fid, dish, name, raw, "measurement-phrase artifact name"))
                continue
            try:
                grams = float(raw)
            except (TypeError, ValueError):
                flagged.append((fid, dish, name, raw, "non-numeric quantity"))
                continue
            if grams <= 0:
                flagged.append((fid, dish, name, grams, "quantity <= 0 (CHECK constraint)"))
                continue
            if grams > IMPLAUSIBLE_G:
                flagged.append((fid, dish, name, grams, f"> {IMPLAUSIBLE_G}g implausible"))
                continue
            proposed.append((fid, dish, name, grams, master_by_norm.get(norm(name))))

    new_master = sorted({name for _, _, name, _, iid in proposed if iid is None})

    print(f"Proposed recipe_ingredients inserts: {len(proposed)}")
    print(f"New ingredients-master rows needed (nutrition left NULL, source='jsonb_backfill'): {len(new_master)}")
    print(f"Flagged (NOT written, needs review): {len(flagged)}\n")
    for fid, dish, name, grams, iid in proposed:
        tag = "" if iid else "  [new master row]"
        print(f"  INSERT fid={fid} ({dish}): {name} = {grams}g{tag}")
    if flagged:
        print("\nFlagged:")
        for fid, dish, name, raw, reason in flagged:
            print(f"  SKIP fid={fid} ({dish}): {name} = {raw!r} — {reason}")

    if not args.write:
        print("\nDry-run only. Re-run with --write to apply.")
        return
    if input("\nApply these inserts? Type Y to confirm: ").strip() != "Y":
        print("Aborted.")
        return

    with engine.begin() as conn:
        for name in new_master:
            iid = conn.execute(text(
                "INSERT INTO ingredients (name, name_normalized, source) "
                "VALUES (:n, :nn, 'jsonb_backfill') "
                "ON CONFLICT (name, source) DO UPDATE SET name = EXCLUDED.name RETURNING id"
            ), {"n": name, "nn": norm(name)}).scalar()
            master_by_norm[norm(name)] = iid
        for fid, _dish, name, grams, iid in proposed:
            conn.execute(text(
                "INSERT INTO recipe_ingredients (food_item_id, ingredient_id, quantity_g) "
                "VALUES (:f, :i, :q)"
            ), {"f": fid, "i": iid or master_by_norm[norm(name)], "q": grams})
    print(f"Applied {len(proposed)} inserts ({len(new_master)} new master ingredients).")


if __name__ == "__main__":
    main()
