"""
44 of the 49 dishes under 50 kcal/serving (see find_dropped_recipe_ingredients.py)
turned out to be fully ingredient-linked already -- they're just small-portion
condiments/drinks/sides mis-tagged into a slot_type meant for full dishes
(sabzi/main_dish/snack_item/dal_protein), which is why they read as "broken"
low-kcal entries in that pool. This reclassifies the ones actually wrong,
verified by looking each unfamiliar name up (see SOURCES) -- most of the 44
were already correctly tagged (Mint Chutney/condiment, Kachumber Salad/
accompaniment, teas/beverage, etc.) and are left alone.

SOURCES (verified 2026-08-04):
  Ranjaka            = red chili chutney/pickle           https://vegrecipesofkarnataka.com/422-ranjaka-recipe-red-chili-chutney-north-karnataka.php
  Karivepaku Pachadi = curry leaf chutney                 https://www.archanaskitchen.com/andhra-style-kavepaku-pachadi-recipe-curry-leaf-chutney-recipe
  Basil Tincture     = concentrated flavoring extract      https://theherbprof.com/holy-basil-tincture-recipe/
  Chukku Kaapi/Copy  = dry-ginger coffee drink             https://www.archanaskitchen.com/recipe/chukku-kaapi-recipe-dry-ginger-coffee
  Sattu salted sorbet = sattu sharbat (savoury drink)      https://rachnacooks.com/sattu-drink-recipe-sattu-ka-namkeen-sharbat/
  Apple Puree        = snack/topping, not a vegetable dish https://www.healthylittlefoodies.com/apple-puree/
  Falsa Sharbat       = "sharbat" = syrup drink by definition, standard term

Not touched (left as-is, not a miscategorization):
  - Carrot Puree stays sabzi -- unlike apple puree it's a savoury vegetable
    mash commonly served as a side dish in this cuisine, not a snack/topping.
  - Masala Chaas is split 3x accompaniment / 1x beverage across near-duplicate
    rows -- both categories are defensible for spiced buttermilk; not a clear
    error, so left alone rather than forcing an arbitrary pick.
  - Hara Dhania Paratha / Baked Amritsari Kulcha stay grain -- they ARE
    breads, just small servings; that's a quantity fact, not a category bug.
  - Dahi Bowl (id 310) is NOT reclassified: retagging dal_protein->accompaniment
    collides with uq_fi_canonical (ids 240/318 already occupy
    (name_normalized='dahi bowl', slot_type='accompaniment', diet_type=
    'Vegetarian')) -- it's a genuine duplicate of an existing entry, which is
    a dedup-pipeline job (scripts/merge_duplicate_dishes.py), not a plain
    slot_type fix. Left as dal_protein and flagged below instead of silently
    dropped.

Usage:
    python -m scripts.reclassify_low_kcal_dishes            # dry run
    python -m scripts.reclassify_low_kcal_dishes --write
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine, text

DATABASE_URL = os.environ["DATABASE_URL"].replace("+asyncpg", "+psycopg2")

# (food_item_id, recipe_name, new_slot_type) -- recipe_name is a sanity check,
# not used in the query, so a stale id can't silently retag the wrong dish.
RECLASSIFY = [
    (3387, "Bottle Gourd & Mint Vegetable Juice", "beverage"),
    (2878, "Ranjaka", "condiment"),
    (2561, "Ranjaka", "condiment"),
    (1735, "Jal Jeera", "beverage"),
    (1499, "Karivepaku Pachadi", "condiment"),
    (2734, "Basil Tincture", "condiment"),
    (3609, "Apple Puree", "snack_item"),
    (1397, "Chukku Copy", "beverage"),
    (1894, "Sattu'S Salted Sorbet", "beverage"),
    (756, "Falsa Sharbat", "beverage"),
]


def main() -> None:
    write = "--write" in sys.argv
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        current = dict(conn.execute(text(
            "SELECT id, recipe_name || '|' || slot_type FROM food_items WHERE id = ANY(:ids)"
        ), {"ids": [fid for fid, _, _ in RECLASSIFY]}).fetchall())

    # One transaction per row -- an integrity-constraint conflict on one dish
    # (e.g. a duplicate under uq_fi_canonical) shouldn't roll back the rest.
    for fid, expected_name, new_slot in RECLASSIFY:
        row = current.get(fid, "")
        name, _, old_slot = row.partition("|")
        if name != expected_name:
            print(f"SKIP food_item_id={fid}: expected {expected_name!r}, found {name!r} (stale id, not touching)")
            continue
        print(f"food_item_id={fid} {name!r}: {old_slot} -> {new_slot}")
        if write:
            try:
                with engine.begin() as conn:
                    conn.execute(text(
                        "UPDATE food_items SET slot_type = :slot WHERE id = :fid"
                    ), {"slot": new_slot, "fid": fid})
            except Exception as e:
                print(f"  FAILED, left unchanged: {e}")

    print("\nDRY RUN. Re-run with --write to apply." if not write else "\ndone.")


if __name__ == "__main__":
    main()
