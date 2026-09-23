"""
Populate `ingredients` micro-nutrient columns from IFCT2017, using the reviewed
ingredient->IFCT map (data/IFCT2017_extracted/ingredient_ifct_map.csv).

Sources (per 100g edible portion):
  Table 5 minerals  -> iron/calcium/sodium/potassium/phosphorus/zinc  (stored mg/100g)
  Table 6 sugars    -> free_sugars/total_sugars                       (stored g/100g)
  Table 7 fat acids -> saturated_fat/mufa/pufa                        (IFCT mg -> stored g/100g)

Cells are "mean" or "mean±SD" -> mean float; blank (below detection) -> NULL (not 0).

Note: sodium IS populated (it's real IFCT data) but per the plan it is NOT used for
filtering — added-salt sodium is unmodeled, so per-dish sodium stays clinically unreliable.

Run: python -m scripts.populate_ingredient_nutrition          # dry run
     python -m scripts.populate_ingredient_nutrition --write
"""
import csv, json, os, re, sys
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))
from dotenv import load_dotenv; load_dotenv()
from sqlalchemy import create_engine, text

BASE = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
EXT = os.path.join(BASE, "data", "IFCT2017_extracted")
MAP_CSV = os.path.join(EXT, "ingredient_ifct_map.csv")

# ingredient column  <-  (table_num, ifct_code, unit_divisor)
# unit_divisor: 1 keeps IFCT units (mg for minerals, g for sugars); 1000 = mg->g (fats)
FIELD_MAP = {
    "iron_per_100g":          (5, "FE",    1),
    "calcium_per_100g":       (5, "CA",    1),
    "sodium_per_100g":        (5, "NA",    1),
    "potassium_per_100g":     (5, "K",     1),
    "phosphorus_per_100g":    (5, "P",     1),
    "zinc_per_100g":          (5, "ZN",    1),
    "free_sugars_per_100g":   (6, "FRSUG", 1),
    "total_sugars_per_100g":  (6, "FRSUG", 1),
    "saturated_fat_per_100g": (7, "FASAT", 1000),
    "mufa_per_100g":          (7, "FAMS",  1000),
    "pufa_per_100g":          (7, "FAPU",  1000),
}


def load_table(n: int) -> dict[str, dict]:
    path = os.path.join(EXT, f"IFCT_Table{n}.json")
    return {r["Food Code"]: r for r in json.load(open(path, encoding="utf-8"))}


def mean(cell) -> float | None:
    """'11.10±0.35' or '9.89' -> float; blank/None -> None."""
    if cell is None or str(cell).strip() == "":
        return None
    head = re.split(r"±", str(cell))[0].strip()
    try:
        return float(head)
    except ValueError:
        return None


def main() -> None:
    write = "--write" in sys.argv
    tables = {n: load_table(n) for n in (5, 6, 7)}
    rows = [r for r in csv.DictReader(open(MAP_CSV, encoding="utf-8")) if r["ifct_code"]]

    updates: list[dict] = []
    filled = {col: 0 for col in FIELD_MAP}
    for r in rows:
        code = r["ifct_code"]
        vals = {}
        for col, (tn, ifct_code, div) in FIELD_MAP.items():
            src = tables[tn].get(code)
            v = mean(src.get(ifct_code)) if src else None
            if v is not None:
                vals[col] = round(v / div, 4)
                filled[col] += 1
            else:
                vals[col] = None
        vals["id"] = int(r["ingredient_id"])
        updates.append(vals)

    print(f"matched ingredients in map: {len(rows)}")
    print("per-column fill counts:", {k: v for k, v in filled.items()})

    if not write:
        # show a sample row
        if updates:
            s = updates[0]
            print("sample:", {k: s[k] for k in ("id", "iron_per_100g", "calcium_per_100g",
                  "sodium_per_100g", "free_sugars_per_100g", "saturated_fat_per_100g")})
        print("\nDry run — pass --write to apply.")
        return

    cols = list(FIELD_MAP)
    set_clause = ", ".join(f"{c} = :{c}" for c in cols)
    eng = create_engine(os.environ["DATABASE_URL"].replace("+asyncpg", "+psycopg2"))
    with eng.begin() as conn:
        for u in updates:
            conn.execute(text(f"UPDATE ingredients SET {set_clause} WHERE id = :id"), u)
    print(f"\nWrote micro-nutrients to {len(updates)} ingredients.")
    print("Next: python -m scripts.recalculate_recipe_nutrition to propagate to food_items.")


if __name__ == "__main__":
    main()
