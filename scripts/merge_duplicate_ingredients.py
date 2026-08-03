"""
Merge duplicate `ingredients` rows and wire the orphaned IFCT 2017 data in.

40 ingredient names exist 2-3 times over. The important part is WHY: the IFCT 2017
import (scripts/import_ifct.py) inserted NEW ingredient rows instead of updating the
existing Gemini-estimated ones, so every one of the 2,944 recipe_ingredients rows on
a duplicated name points at an `estimated_llm` row while the authoritative IFCT2017
row sits at zero usage. Merging therefore also fixes nutrition accuracy -- e.g. milk
61 -> 107.31 kcal/100g, drumstick 78 -> 29.4.

Winner per duplicate-name group:
  1. source = 'IFCT2017'                      (15 groups -- authoritative)
  2. else all members field-identical -> lowest id   (23 groups -- zero impact)
  3. else patch the survivor with IFCT values  (peanuts, tur dal -- see IFCT_PATCH)

Safe by construction: no dish references two ids of the same group (verified zero
collision groups), so repointing can never violate uq_recipe_ingredient.

Usage:
    python -m scripts.merge_duplicate_ingredients            # dry run
    python -m scripts.merge_duplicate_ingredients --write
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
sys.path.insert(0, str(PROJECT_ROOT))

DATABASE_URL = os.environ["DATABASE_URL"].replace("+asyncpg", "+psycopg2")

NUTRITION_FIELDS = [
    "calories_per_100g", "protein_per_100g", "carbs_per_100g", "fat_per_100g",
    "fiber_per_100g", "sodium_per_100g", "iron_per_100g", "calcium_per_100g",
    "potassium_per_100g", "phosphorus_per_100g", "zinc_per_100g",
    "total_sugars_per_100g", "free_sugars_per_100g", "saturated_fat_per_100g",
    "mufa_per_100g", "pufa_per_100g", "unit_weight_g",
]

# The two groups where both members are LLM guesses that disagree. Values taken from
# data/IFCT2017_extracted/IFCT_Table1.xlsx (energy column is kJ; kcal = kJ / 4.184).
#   peanuts -> H012 "Ground nut (Arachis hypogaea)"  2176 kJ
#   tur dal -> B021 "Red gram, dal (Cajanus cajan)"  1384 kJ
IFCT_PATCH = {
    "peanuts": {
        "calories_per_100g": 520.1, "protein_per_100g": 23.65, "fat_per_100g": 39.63,
        "carbs_per_100g": 17.27, "fiber_per_100g": 10.38,
        "_src": "IFCT2017 H012 Ground nut",
    },
    "tur dal": {
        "calories_per_100g": 330.8, "protein_per_100g": 21.70, "fat_per_100g": 3.26,
        "carbs_per_100g": 55.23, "fiber_per_100g": 9.06,
        "_src": "IFCT2017 B021 Red gram, dal",
    },
}


def pick_winner(members: list[dict]) -> tuple[dict, str]:
    """Return (winner_row, reason)."""
    ifct = [m for m in members if m["source"] == "IFCT2017"]
    if ifct:
        return min(ifct, key=lambda m: m["id"]), "IFCT2017 authoritative"
    signatures = {tuple(str(m[f]) for f in NUTRITION_FIELDS) for m in members}
    if len(signatures) == 1:
        return min(members, key=lambda m: m["id"]), "identical values, lowest id"
    return min(members, key=lambda m: m["id"]), "values differ -> patched from IFCT"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true", help="apply (default is dry run)")
    args = ap.parse_args()

    engine = create_engine(DATABASE_URL)
    cols = "id, name, source, " + ", ".join(NUTRITION_FIELDS)

    with engine.begin() as conn:
        rows = [dict(r._mapping) for r in conn.execute(text(
            f"SELECT {cols} FROM ingredients ORDER BY id"
        ))]
        usage = dict(conn.execute(text(
            "SELECT ingredient_id, count(*) FROM recipe_ingredients GROUP BY 1"
        )).all())

        groups: dict[str, list[dict]] = defaultdict(list)
        for r in rows:
            groups[(r["name"] or "").strip().lower()].append(r)
        dupes = {k: v for k, v in groups.items() if len(v) > 1}

        print(f"{len(rows):,} ingredients, {len(dupes)} duplicated names\n")

        plan, patches, total_moved, total_losers = [], [], 0, 0
        for name, members in sorted(dupes.items()):
            winner, reason = pick_winner(members)
            losers = [m for m in members if m["id"] != winner["id"]]
            moved = sum(usage.get(m["id"], 0) for m in losers)
            total_moved += moved
            total_losers += len(losers)
            plan.append((name, winner, losers, reason, moved))
            if name in IFCT_PATCH:
                patches.append((name, winner))

        print(f"{'ingredient':<20}{'winner':<9}{'losers':<12}{'rows moved':<12}reason")
        for name, w, losers, reason, moved in plan:
            w_cal = w["calories_per_100g"]
            l_ids = ",".join(str(x["id"]) for x in losers)
            print(f"  {name[:18]:<18}{w['id']:<9}{l_ids:<12}{moved:<12}{reason}")
            if reason.startswith("IFCT2017"):
                for lo in losers:
                    if str(lo["calories_per_100g"]) != str(w_cal):
                        print(f"      cal/100g {lo['calories_per_100g']} -> {w_cal}"
                              f"   ({usage.get(lo['id'], 0)} recipe rows)")

        if patches:
            print("\nIFCT value patches applied to the surviving row:")
            for name, w in patches:
                p = IFCT_PATCH[name]
                print(f"  id={w['id']} {name}: cal {w['calories_per_100g']} -> "
                      f"{p['calories_per_100g']}  [{p['_src']}]")

        print(f"\n  loser rows to delete   : {total_losers}")
        print(f"  recipe rows to repoint : {total_moved:,}")

        if not args.write:
            print("\nDRY RUN. Re-run with --write to apply.")
            return

        confirm = input(f"\nApply {total_losers} merges? Type Y: ").strip()
        if confirm != "Y":
            print("Aborted -- nothing written.")
            return

        repointed = 0
        for name, winner, losers, reason, _ in plan:
            wid = winner["id"]

            if name in IFCT_PATCH:
                p = {k: v for k, v in IFCT_PATCH[name].items() if not k.startswith("_")}
                sets = ", ".join(f"{k} = :{k}" for k in p)
                conn.execute(text(
                    f"UPDATE ingredients SET {sets}, source = 'IFCT2017' WHERE id = :wid"
                ), {**p, "wid": wid})
                conn.execute(text(
                    "INSERT INTO data_change_audit_log (request_id, target_table, target_id,"
                    " action, field_changed, before_value, after_value, actor, reason)"
                    " VALUES (NULL, 'ingredients', :wid, 'update', 'nutrition',"
                    " CAST(:before AS jsonb), CAST(:after AS jsonb), 'system:ingredient_merge', :reason)"
                ), {"wid": wid,
                    "before": json.dumps({f: str(winner[f]) for f in NUTRITION_FIELDS}),
                    "after": json.dumps({k: str(v) for k, v in p.items()}),
                    "reason": f"adopted {IFCT_PATCH[name]['_src']}"})

            for lo in losers:
                lid = lo["id"]
                res = conn.execute(text(
                    "UPDATE recipe_ingredients SET ingredient_id = :wid WHERE ingredient_id = :lid"
                ), {"wid": wid, "lid": lid})
                repointed += res.rowcount
                conn.execute(text(
                    "INSERT INTO data_change_audit_log (request_id, target_table, target_id,"
                    " action, field_changed, before_value, after_value, actor, reason)"
                    " VALUES (NULL, 'ingredients', :lid, 'merge', 'id',"
                    " CAST(:before AS jsonb), CAST(:after AS jsonb), 'system:ingredient_merge', :reason)"
                ), {"lid": lid,
                    "before": json.dumps({"id": lid, "name": lo["name"], "source": lo["source"],
                                          **{f: str(lo[f]) for f in NUTRITION_FIELDS}}),
                    "after": json.dumps({"merged_into": wid, "rows_repointed": res.rowcount}),
                    "reason": f"duplicate of #{wid} ({name}) -- {reason}"})
                conn.execute(text("DELETE FROM ingredients WHERE id = :lid"), {"lid": lid})

        print(f"\nRepointed {repointed:,} recipe_ingredients rows; deleted {total_losers} ingredients.")
        print("Next: python -m scripts.recalculate_recipe_nutrition")


if __name__ == "__main__":
    main()
