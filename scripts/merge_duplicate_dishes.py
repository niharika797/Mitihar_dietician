"""Tier-1 exact-duplicate merge — soft-delete redundant food_items rows.

READ-ONLY by default. Pass --write (and type Y) to apply.

Unit of grouping is the CANONICAL KEY (name_normalized, slot_type, diet_type) — the same
key as the uq_fi_canonical partial-unique index. This naturally keeps diet-variants
(same name, different diet_type) in separate groups, so they are never merged.

A group is Tier-1 (safe auto-merge) only when every verified+live row in it is byte-identical
on all 7 macro fields AND its recipe_ingredients set (ingredient_id, quantity_g). Otherwise it
is a Tier-2 conflict — left untouched here for scripts/resolve_dish_conflicts.py.

Merge action per group:
  - canonical = lowest id (all rows are verified+live and, being Tier-1, identical).
  - losers get deleted_at = now() (SOFT delete; row stays, FKs stay valid).
  - Only patient_dish_preferences is repointed loser->canonical: it is the sole table whose
    stale pointer to a merged-away dish changes CURRENT behaviour (a pin/block silently stops
    boosting the canonical twin). History/training tables (meal_logs, meal_ratings,
    doctor_meal_overrides, patient_meal_choices*) are intentionally NOT repointed — they must
    stay truthful about the id actually acted on, and the soft-deleted row keeps their FK valid.
    The loser->canonical mapping is preserved in data_change_audit_log for any future rollup.
"""
import argparse
import json
import os
import re
from collections import defaultdict

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import create_engine, text

DATABASE_URL = os.environ["DATABASE_URL"].replace("+asyncpg", "+psycopg2")
engine = create_engine(DATABASE_URL)

MACRO_FIELDS = ("cal_per_serving", "protein_per_serving", "carbs_per_serving",
                "fat_per_serving", "fiber_per_serving", "sodium_per_serving", "serving_weight_g")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def load_groups(conn):
    rows = conn.execute(text(
        "SELECT id, recipe_name, name_normalized, slot_type, diet_type, "
        + ", ".join(MACRO_FIELDS) +
        " FROM food_items WHERE is_verified AND deleted_at IS NULL ORDER BY id"
    )).mappings().all()
    ri = conn.execute(text(
        "SELECT food_item_id, ingredient_id, quantity_g FROM recipe_ingredients"
    )).all()
    ing = defaultdict(set)
    for fid, ing_id, qty in ri:
        ing[fid].add((ing_id, str(qty)))

    groups = defaultdict(list)
    for r in rows:
        key = (r["name_normalized"] or norm(r["recipe_name"]), r["slot_type"], r["diet_type"])
        groups[key].append(r)
    return {k: g for k, g in groups.items() if len(g) > 1}, ing


def macro_sig(r):
    return tuple(str(r[f]) for f in MACRO_FIELDS)


def classify(group, ing):
    sigs = {(macro_sig(r), frozenset(ing[r["id"]])) for r in group}
    return "tier1" if len(sigs) == 1 else "tier2"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="apply the merges (else dry-run)")
    args = ap.parse_args()

    with engine.begin() as conn:
        dup_groups, ing = load_groups(conn)
        tier1 = {k: g for k, g in dup_groups.items() if classify(g, ing) == "tier1"}
        tier2 = {k: g for k, g in dup_groups.items() if classify(g, ing) == "tier2"}

        merges = []  # (canonical_id, loser_row)
        for key, g in sorted(tier1.items()):
            g_sorted = sorted(g, key=lambda r: r["id"])
            canonical = g_sorted[0]
            for loser in g_sorted[1:]:
                merges.append((canonical["id"], loser, key))

        print(f"Canonical-key duplicate groups (verified+live): {len(dup_groups)}")
        print(f"  Tier-1 exact (auto-merge):  {len(tier1)} groups -> {len(merges)} rows to soft-delete")
        print(f"  Tier-2 conflict (skipped):  {len(tier2)} groups (for resolve_dish_conflicts.py)")
        print()
        for cid, loser, key in merges:
            print(f"  merge #{loser['id']:>5} '{loser['recipe_name']}' -> canonical #{cid}  "
                  f"[{key[1]}/{key[2]}]  {loser['cal_per_serving']}kcal")

        if not args.write:
            print(f"\nDRY-RUN. {len(merges)} rows would be soft-deleted. Re-run with --write to apply.")
            return

        confirm = input(f"\nApply {len(merges)} merges (soft-delete + repoint prefs + audit)? Type Y: ").strip()
        if confirm != "Y":
            print("Aborted.")
            return

        for cid, loser, key in merges:
            lid = loser["id"]
            # 1. avoid uq_patient_dish_preference collision, then repoint
            conn.execute(text(
                "DELETE FROM patient_dish_preferences p WHERE p.food_item_id = :lid "
                "AND EXISTS (SELECT 1 FROM patient_dish_preferences q "
                "WHERE q.patient_id = p.patient_id AND q.food_item_id = :cid)"
            ), {"lid": lid, "cid": cid})
            conn.execute(text(
                "UPDATE patient_dish_preferences SET food_item_id = :cid WHERE food_item_id = :lid"
            ), {"lid": lid, "cid": cid})
            # 2. soft-delete the loser
            conn.execute(text(
                "UPDATE food_items SET deleted_at = now() WHERE id = :lid AND deleted_at IS NULL"
            ), {"lid": lid})
            # 3. audit
            before = {"id": lid, "recipe_name": loser["recipe_name"],
                      **{f: str(loser[f]) for f in MACRO_FIELDS}}
            conn.execute(text(
                "INSERT INTO data_change_audit_log "
                "(request_id, target_table, target_id, action, field_changed, before_value, after_value, actor, reason) "
                "VALUES (NULL, 'food_items', :tid, 'merge', 'deleted_at', "
                "CAST(:before AS jsonb), CAST(:after AS jsonb), 'system:tier1_auto', :reason)"
            ), {"tid": lid, "before": json.dumps(before),
                "after": json.dumps({"merged_into": cid}),
                "reason": f"exact-duplicate of #{cid} ({key[0]} / {key[1]} / {key[2]})"})

        print(f"Applied {len(merges)} merges. Soft-deleted {len(merges)} rows; audit rows written.")


if __name__ == "__main__":
    main()
