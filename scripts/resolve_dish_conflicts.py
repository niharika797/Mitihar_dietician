"""Tier-2 conflict resolution — recompute-first, then merge-or-park.

READ-ONLY by default. Pass --write (and type Y) to apply.

A Tier-2 group = same canonical key (name_normalized, slot_type, diet_type) with >1
verified+live row whose macros/ingredients differ. Most are the 6k-dataset scaling bug
(one row stores whole-recipe kcal, its twin stores per-serving). Strategy:

  1. Recompute every row's macros bottom-up from its recipe_ingredients (pure function of the
     ingredient set), using scripts/recalculate_recipe_nutrition.py's formula + a 0.80 coverage
     gate and a 50..1500 kcal sanity gate. Recomputable rows get their corrected macros WRITTEN
     (nutrition_source='calculated') — this fixes the scaling bug at the source.
  2. Canonical = the recomputable row with the lowest id (else lowest id overall).
  3. For each other row: if it recomputes to the SAME macros AND has the SAME ingredient set as
     canonical, it is now an exact duplicate -> soft-delete (merge, audit). Otherwise it is a
     GENUINE conflict -> PARK it (is_verified=False, removed from the served pool) and file a
     pending DataChangeRequest for admin review. Never auto-pick between genuine conflicts.

Postcondition: every canonical-key group ends with exactly ONE verified+live row, so the
uq_fi_canonical unique index can then build.
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
COVERAGE_THRESHOLD = 0.80
CAL_MIN, CAL_MAX = 50.0, 1500.0


def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def load(conn):
    rows = conn.execute(text(
        "SELECT id, recipe_name, name_normalized, slot_type, diet_type, nutrition_source, "
        + ", ".join(MACRO_FIELDS) +
        " FROM food_items WHERE is_verified AND deleted_at IS NULL ORDER BY id"
    )).mappings().all()
    ri = conn.execute(text("""
        SELECT ri.food_item_id, ri.ingredient_id, ri.quantity_g,
               ing.calories_per_100g, ing.protein_per_100g, ing.carbs_per_100g,
               ing.fat_per_100g, ing.fiber_per_100g, ing.sodium_per_100g
        FROM recipe_ingredients ri JOIN ingredients ing ON ing.id = ri.ingredient_id
    """)).all()
    by_food = defaultdict(list)
    for r in ri:
        by_food[r[0]].append(r)
    groups = defaultdict(list)
    for r in rows:
        groups[(r["name_normalized"] or norm(r["recipe_name"]), r["slot_type"], r["diet_type"])].append(r)
    return {k: g for k, g in groups.items() if len(g) > 1}, by_food


def ing_set(rows):
    # compare quantity as a rounded float so cosmetic formatting (100.0 vs 100.00) doesn't
    # register as a different ingredient set and over-park a genuine duplicate.
    return frozenset((r[1], round(float(r[2]), 3)) for r in rows)


def recompute(rows):
    """Return (macros dict, coverage) or (None, coverage) if not sane/covered."""
    if not rows:
        return None, 0.0
    covered = sum(1 for r in rows if r[3] is not None and r[4] is not None
                  and r[5] is not None and r[6] is not None)
    coverage = covered / len(rows)
    if coverage < COVERAGE_THRESHOLD:
        return None, coverage
    q = lambda idx: sum((float(r[idx] or 0)) * float(r[2]) / 100 for r in rows)
    cal = q(3)
    if not (CAL_MIN <= cal <= CAL_MAX):
        return None, coverage
    macros = {
        "cal_per_serving": round(cal, 2), "protein_per_serving": round(q(4), 2),
        "carbs_per_serving": round(q(5), 2), "fat_per_serving": round(q(6), 2),
        "fiber_per_serving": round(q(7), 2), "sodium_per_serving": round(q(8), 2),
        "serving_weight_g": round(sum(float(r[2]) for r in rows), 1),
    }
    return macros, coverage


def sig(macros):
    return tuple(str(macros[f]) for f in MACRO_FIELDS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()

    with engine.begin() as conn:
        groups, by_food = load(conn)
        # only groups still conflicting (macros or ingredients differ)
        tier2 = {}
        for k, g in groups.items():
            sigs = {(tuple(str(r[f]) for f in MACRO_FIELDS), ing_set(by_food[r["id"]])) for r in g}
            if len(sigs) > 1:
                tier2[k] = g

        merges, parks, writes = [], [], []  # (loser,canonical,key) / (row,recomp,key) / (id,macros)
        for key, g in sorted(tier2.items()):
            recomp = {r["id"]: recompute(by_food[r["id"]]) for r in g}
            for r in g:
                m, _ = recomp[r["id"]]
                if m is not None:
                    writes.append((r["id"], m))
            recomputable = [r for r in g if recomp[r["id"]][0] is not None]
            canonical = min(recomputable or g, key=lambda r: r["id"])
            cmac = recomp[canonical["id"]][0]
            cset = ing_set(by_food[canonical["id"]])
            for r in g:
                if r["id"] == canonical["id"]:
                    continue
                rmac = recomp[r["id"]][0]
                if rmac is not None and cmac is not None and sig(rmac) == sig(cmac) \
                        and ing_set(by_food[r["id"]]) == cset:
                    merges.append((r, canonical["id"], key))
                else:
                    parks.append((r, rmac, key, canonical["id"], cmac))

        print(f"Tier-2 conflict groups (still divergent): {len(tier2)}")
        print(f"  rows recomputed & rewritten (scaling-bug fix): {len(writes)}")
        print(f"  converged -> soft-delete merge:               {len(merges)}")
        print(f"  genuine conflict -> park + DataChangeRequest:  {len(parks)}")
        print()
        for r, rmac, key, cid, cmac in parks[:40]:
            new_cal = rmac['cal_per_serving'] if rmac else 'un-recomputable'
            print(f"  PARK #{r['id']:>5} '{r['recipe_name']}' [{key[1]}/{key[2]}] "
                  f"stored {r['cal_per_serving']}kcal -> recomputed {new_cal}  (kept canonical #{cid})")

        if not args.write:
            print(f"\nDRY-RUN. Re-run with --write to apply.")
            return
        if input(f"\nApply: rewrite {len(writes)}, merge {len(merges)}, park {len(parks)}? Type Y: ").strip() != "Y":
            print("Aborted.")
            return

        # 1. write recomputed macros (fix scaling bug)
        for fid, m in writes:
            conn.execute(text(
                "UPDATE food_items SET cal_per_serving=:cal_per_serving, protein_per_serving=:protein_per_serving, "
                "carbs_per_serving=:carbs_per_serving, fat_per_serving=:fat_per_serving, "
                "fiber_per_serving=:fiber_per_serving, sodium_per_serving=:sodium_per_serving, "
                "serving_weight_g=:serving_weight_g, nutrition_source='calculated' WHERE id=:fid"
            ), {**m, "fid": fid})
        # 2. merge converged losers (soft-delete + repoint prefs + audit)
        for loser, cid, key in merges:
            lid = loser["id"]
            conn.execute(text(
                "DELETE FROM patient_dish_preferences p WHERE p.food_item_id=:lid AND EXISTS "
                "(SELECT 1 FROM patient_dish_preferences q WHERE q.patient_id=p.patient_id AND q.food_item_id=:cid)"
            ), {"lid": lid, "cid": cid})
            conn.execute(text("UPDATE patient_dish_preferences SET food_item_id=:cid WHERE food_item_id=:lid"),
                         {"lid": lid, "cid": cid})
            conn.execute(text("UPDATE food_items SET deleted_at=now() WHERE id=:lid AND deleted_at IS NULL"),
                         {"lid": lid})
            conn.execute(text(
                "INSERT INTO data_change_audit_log (request_id,target_table,target_id,action,field_changed,"
                "before_value,after_value,actor,reason) VALUES (NULL,'food_items',:tid,'merge','deleted_at',"
                "CAST(:b AS jsonb),CAST(:a AS jsonb),'system:ai_observer',:r)"
            ), {"tid": lid, "b": json.dumps({"id": lid, "recipe_name": loser["recipe_name"]}),
                "a": json.dumps({"merged_into": cid}),
                "r": f"recompute-converged duplicate of #{cid} ({key[0]} / {key[1]} / {key[2]})"})
        # 3. park genuine conflicts (unverify + DataChangeRequest + audit)
        for r, rmac, key, cid, cmac in parks:
            pid = r["id"]
            conn.execute(text("UPDATE food_items SET is_verified=false WHERE id=:pid"), {"pid": pid})
            old = {f: str(r[f]) for f in MACRO_FIELDS}
            kept_cal = cmac["cal_per_serving"] if cmac else "?"
            if rmac is None:
                detail = "Cannot recompute this row (missing/low-coverage ingredient nutrition); needs manual review."
            elif abs(float(rmac["cal_per_serving"]) - float(r["cal_per_serving"])) > 1:
                detail = f"Recompute corrected stored {r['cal_per_serving']}->{rmac['cal_per_serving']} kcal, still differs from kept #{cid} ({kept_cal} kcal)."
            else:
                detail = f"Distinct recipe/serving under a shared name; kept canonical #{cid} ({kept_cal} kcal). Confirm keep-parked or promote this one."
            reason = f"Same-name conflict ({key[0]} / {key[1]} / {key[2]}). " + detail
            conn.execute(text(
                "INSERT INTO data_change_requests (target_table,target_id,field_changed,old_value,new_value,"
                "proposed_by,proposal_reason,tier,status) VALUES ('food_items',:tid,'cal_per_serving',"
                "CAST(:old AS jsonb),CAST(:new AS jsonb),'system:ai_observer',:reason,'tier2_review','pending')"
            ), {"tid": pid, "old": json.dumps(old),
                "new": json.dumps(rmac) if rmac else json.dumps(None), "reason": reason})
            conn.execute(text(
                "INSERT INTO data_change_audit_log (request_id,target_table,target_id,action,field_changed,"
                "before_value,after_value,actor,reason) VALUES (NULL,'food_items',:tid,'proposed','is_verified',"
                "CAST(:b AS jsonb),CAST(:a AS jsonb),'system:ai_observer',:r)"
            ), {"tid": pid, "b": json.dumps({"is_verified": True}), "a": json.dumps({"is_verified": False}),
                "r": "parked from served pool pending Tier-2 conflict review"})

        print(f"Applied. Rewrote {len(writes)}, merged {len(merges)}, parked {len(parks)}.")


if __name__ == "__main__":
    main()
