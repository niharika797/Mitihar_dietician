"""
Derive medical avoid/prefer tags on food_items from computed per-serving nutrition
(the IFCT-backed columns filled by compute_dish_micronutrients.py), replacing sparse
LLM-guessed tags with data-backed ones. Thresholds: docs/MEDICAL_THRESHOLDS.md.

The generator already filters on these tags (tag_utils.py) — nothing downstream changes.

Semantics (idempotent, re-runnable):
  * Only rows with tags_locked = false are touched (doctor overrides are preserved).
  * A rule OWNS its tag only when the gating nutrient is non-NULL: data present ->
    add if the rule matches, remove if it doesn't. Gating nutrient NULL -> the tag is
    left exactly as-is (never tag/untag on unknown data).
  * Non-medical tags already on the row (e.g. avoid_gluten) are always preserved.

Run: python -m scripts.derive_medical_tags          # dry run (stats only)
     python -m scripts.derive_medical_tags --write
"""
import os, sys
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))
from dotenv import load_dotenv; load_dotenv()
from sqlalchemy import create_engine, text

# Tunable clinical cutoffs on the base serving — see docs/MEDICAL_THRESHOLDS.md.
SUGAR_HIGH   = 10.0   # g free sugars -> avoid_diabetes / avoid_pcos
SUGAR_LOW    = 5.0    # g free sugars -> (with fibre) diabetes_friendly
FIBER_MIN    = 3.0    # g fibre floor for diabetes_friendly
SATFAT_HIGH  = 5.0    # g saturated fat -> avoid_highchol / avoid_heart
SATFAT_LOW   = 2.0    # g saturated fat -> heart_friendly / cholesterol_friendly
CALCIUM_RICH = 200.0  # mg -> calcium_rich (>=20% of 1000 mg RDA)
IRON_RICH    = 3.5    # mg -> iron_rich (~>=20% of adult RDA)

# (tag, kind, gate_field, predicate). The tag is MANAGED only where gate_field is non-NULL.
# predicate(f) receives the food row as a dict of floats (gate already known non-NULL).
RULES = [
    ("avoid_diabetes",       "avoid",  "free_sugars_per_serving",   lambda f: f["fs"] > SUGAR_HIGH),
    ("avoid_pcos",           "avoid",  "free_sugars_per_serving",   lambda f: f["fs"] > SUGAR_HIGH),
    ("diabetes_friendly",    "prefer", "free_sugars_per_serving",   lambda f: f["fs"] < SUGAR_LOW and f["fib"] >= FIBER_MIN),
    ("avoid_highchol",       "avoid",  "saturated_fat_per_serving", lambda f: f["sf"] > SATFAT_HIGH),
    ("avoid_heart",          "avoid",  "saturated_fat_per_serving", lambda f: f["sf"] > SATFAT_HIGH),
    ("heart_friendly",       "prefer", "saturated_fat_per_serving", lambda f: f["sf"] < SATFAT_LOW),
    ("cholesterol_friendly", "prefer", "saturated_fat_per_serving", lambda f: f["sf"] < SATFAT_LOW),
    ("calcium_rich",         "prefer", "calcium_per_serving",       lambda f: f["ca"] >= CALCIUM_RICH),
    ("iron_rich",            "prefer", "iron_per_serving",          lambda f: f["fe"] >= IRON_RICH),
]


def _num(v):
    return None if v is None else float(v)


def apply_rules(avoid: set, prefer: set, f: dict, gate: dict) -> tuple[set, set]:
    """Own a managed tag only where its gate nutrient is non-NULL: add if the rule
    matches, remove if it doesn't. NULL gate -> leave that tag untouched. Non-managed
    tags in avoid/prefer are never touched. Returns the mutated (avoid, prefer)."""
    for tag, kind, gate_field, pred in RULES:
        if gate[gate_field] is None:
            continue
        target = avoid if kind == "avoid" else prefer
        want = pred(f)
        if want:
            target.add(tag)
        else:
            target.discard(tag)
    return avoid, prefer


def _selftest() -> None:
    G = ["free_sugars_per_serving", "saturated_fat_per_serving", "calcium_per_serving", "iron_per_serving"]
    # high sugar + high satfat -> avoid tags added, friendly removed; gluten preserved
    a, p = apply_rules({"avoid_gluten"}, set(),
                       {"fs": 15, "sf": 8, "ca": 50, "fe": 1, "fib": 1},
                       {"free_sugars_per_serving": 15, "saturated_fat_per_serving": 8,
                        "calcium_per_serving": 50, "iron_per_serving": 1})
    assert a == {"avoid_gluten", "avoid_diabetes", "avoid_pcos", "avoid_highchol", "avoid_heart"}, a
    assert p == set(), p
    # low sugar+fibre, low satfat, rich Ca/Fe -> prefer tags; stale avoid_diabetes removed (data present)
    a, p = apply_rules({"avoid_diabetes"}, set(),
                       {"fs": 2, "sf": 1, "ca": 300, "fe": 5, "fib": 4},
                       {"free_sugars_per_serving": 2, "saturated_fat_per_serving": 1,
                        "calcium_per_serving": 300, "iron_per_serving": 5})
    assert a == set(), a
    assert p == {"diabetes_friendly", "heart_friendly", "cholesterol_friendly", "calcium_rich", "iron_rich"}, p
    # NULL sugar gate -> existing avoid_diabetes left intact (never untag on unknown data)
    a, p = apply_rules({"avoid_diabetes"}, set(),
                       {"fs": None, "sf": None, "ca": None, "fe": None, "fib": 0},
                       {g: None for g in G})
    assert a == {"avoid_diabetes"} and p == set(), (a, p)
    print("selftest OK")


def main() -> None:
    if "--selftest" in sys.argv:
        _selftest(); return
    write = "--write" in sys.argv
    eng = create_engine(os.environ["DATABASE_URL"].replace("+asyncpg", "+psycopg2"))

    with eng.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, avoid_tags, prefer_tags, tags_locked,
                   free_sugars_per_serving, saturated_fat_per_serving,
                   calcium_per_serving, iron_per_serving, fiber_per_serving
            FROM food_items ORDER BY id
        """)).mappings().all()

    locked = changed = 0
    added = {r[0]: 0 for r in RULES}
    removed = {r[0]: 0 for r in RULES}
    final = {r[0]: 0 for r in RULES}
    updates: list[dict] = []

    for r in rows:
        if r["tags_locked"]:
            locked += 1
            continue
        f = {"fs": _num(r["free_sugars_per_serving"]), "sf": _num(r["saturated_fat_per_serving"]),
             "ca": _num(r["calcium_per_serving"]), "fe": _num(r["iron_per_serving"]),
             "fib": float(r["fiber_per_serving"] or 0)}
        gate = {"free_sugars_per_serving": f["fs"], "saturated_fat_per_serving": f["sf"],
                "calcium_per_serving": f["ca"], "iron_per_serving": f["fe"]}

        old_a, old_p = set(r["avoid_tags"] or []), set(r["prefer_tags"] or [])
        avoid, prefer = apply_rules(set(old_a), set(old_p), f, gate)
        for tag, kind, *_ in RULES:
            src, was = (avoid, old_a) if kind == "avoid" else (prefer, old_p)
            if tag in src and tag not in was:
                added[tag] += 1
            elif tag not in src and tag in was:
                removed[tag] += 1
            if tag in src:
                final[tag] += 1

        if avoid != old_a or prefer != old_p:
            changed += 1
            updates.append({"id": r["id"], "a": sorted(avoid), "p": sorted(prefer)})

    print(f"food_items: {len(rows)} | locked(skipped): {locked} | rows changed: {changed}")
    print(f"{'tag':22} {'added':>7} {'removed':>8} {'final':>7}")
    for tag, *_ in RULES:
        print(f"  {tag:20} {added[tag]:>7} {removed[tag]:>8} {final[tag]:>7}")

    if not write:
        print("\nDry run — pass --write to apply.")
        return

    with eng.begin() as conn:
        for u in updates:
            conn.execute(text(
                "UPDATE food_items SET avoid_tags = CAST(:a AS jsonb), "
                "prefer_tags = CAST(:p AS jsonb) WHERE id = :id"),
                {"id": u["id"], "a": _json(u["a"]), "p": _json(u["p"])})
    print(f"\nWrote tags to {len(updates)} food_items.")


def _json(lst) -> str:
    import json
    return json.dumps(lst)


if __name__ == "__main__":
    main()
