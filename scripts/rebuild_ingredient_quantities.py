"""
Rebuild single-serving quantity_g from the pre-damage backup.

Baseline is db-backups/mityahar_content_2026-07-31.sql, NOT the live DB: the live
values still carry the damage from the deprecated fix_ingredient_quantities.py
(flat-value collapse, the `clove`->garlic keyword collision, the flat 180g cap,
and the flat 400/450g dish rescale).

Root cause this corrects: the original ingest converted every COUNTED ingredient
at a flat 80g per piece regardless of what it is. Verified against the source
dataset (data/6000+ Indian Food Recipes Dataset/) -- implied grams-per-count is
exactly 80.0. That is right for onion/tomato/potato (~80g each) and catastrophically
wrong for chillies, garlic, bay leaf and curry leaf. A partial earlier fix left a
second cluster at 1/10 scale, so counts 1-4 appear as both 80/160/240/320 and
8/16/24/32.

Deliberately NOT dividing by the source `Servings` column: tested, and it drops
78.8% of dishes below 150g total, which is implausible for a single serving.

Writes ONLY into data/review/recipe_ingredients_review.csv's quantity_g_corrected
column. Nothing here touches Postgres -- review the CSV, then run
scripts/import_recipe_ingredients_review.py.

Usage:
    python -m scripts.rebuild_ingredient_quantities
    python -m scripts.rebuild_ingredient_quantities --dry-run   # report only, no write
"""

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.sanity_check_ingredients import (  # noqa: E402
    DISH_TOTAL_DEFAULT,
    DISH_TOTAL_MAX,
    categorize_ingredient,
)

BACKUP_SQL = PROJECT_ROOT / "db-backups" / "mityahar_content_2026-07-31.sql"
REVIEW_CSV = PROJECT_ROOT / "data" / "review" / "recipe_ingredients_review.csv"

# Grams per PIECE for ingredients the ingest counted rather than weighed.
# Sources: docs/audits/sanity_check_research.md SS3I (whole spices) and SS3K
# (fresh herbs & aromatics), IFCT 2017 unit weights.
# Ingredients genuinely ~80g/piece (onion, tomato, potato, carrot, capsicum) are
# deliberately absent -- the ingest's 80g was already correct for those.
PIECE_WEIGHT_G = {
    "curry leaves": 0.15, "curry leaf": 0.15,   # IFCT: 0.1-0.2g per leaf
    "bay leaves": 0.5, "bay leaf": 0.5,         # ~0.5g per leaf
    "green chillies": 4.0, "green chilli": 4.0,
    "green chilies": 4.0, "green chili": 4.0,   # TradeIndia: 2-5g per piece
    "dry red chillies": 2.0, "dry red chilli": 2.0,
    "dry red chilies": 2.0, "dry red chili": 2.0,
    "red chillies": 2.0, "red chilies": 2.0,
    "cloves garlic": 5.0, "garlic": 5.0,        # 3-7g per clove
    "black cardamom": 2.0,                      # ~2g per pod
    "cardamom": 0.2,                            # green: 0.15-0.25g per pod
    "cinnamon": 2.0,                            # 1.5-2.5g per small stick
    "star anise": 1.0,
    "cloves": 0.07, "clove": 0.07,              # ~0.07g each
    "long": 0.07, "lavang": 0.07,               # laung = clove
}

# Only piece-correct within these categories. Keeps "Red chilli powder"
# (powder_spice) from being treated as a count of chillies.
PIECE_CATEGORIES = {"curry_leaf", "whole_spice", "aromatic"}


def piece_weight(name: str) -> float | None:
    """Longest-keyword match, same convention as categorize_ingredient()."""
    nl = name.lower().strip()
    best, best_len = None, 0
    for kw, grams in PIECE_WEIGHT_G.items():
        if kw in nl and len(kw) > best_len:
            best, best_len = grams, len(kw)
    return best


def load_backup() -> tuple[dict, dict, dict]:
    """Parse the pg_dump COPY blocks we need. Returns (recipe_ingredients, ingredient_names, slot_types)."""
    lines = BACKUP_SQL.read_text(encoding="utf-8").splitlines()

    def block(prefix: str) -> list[list[str]]:
        start = next(i for i, l in enumerate(lines) if l.startswith(prefix))
        rows = []
        for l in lines[start + 1:]:
            if l == "\\.":
                break
            rows.append(l.split("\t"))
        return rows

    ing_names = {p[0]: p[1] for p in block("COPY public.ingredients")}

    fi_header = next(l for l in lines if l.startswith("COPY public.food_items"))
    fi_cols = fi_header[fi_header.index("(") + 1:fi_header.index(")")].split(", ")
    slot_idx = fi_cols.index("slot_type")
    slots = {p[0]: p[slot_idx] for p in block("COPY public.food_items")}

    # ri_id -> (food_item_id, ingredient_name, quantity_g)
    ri = {
        p[0]: (p[1], ing_names.get(p[2], ""), float(p[3]))
        for p in block("COPY public.recipe_ingredients")
    }
    return ri, slots, ing_names


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="report only, don't write the CSV")
    args = ap.parse_args()

    ri, slots, _ = load_backup()
    print(f"Loaded {len(ri):,} rows from {BACKUP_SQL.name} (pre-damage baseline).")

    corrected: dict[str, float] = {}
    reason: dict[str, str] = {}
    stats = defaultdict(int)

    # --- Pass 1: piece-weight correction --------------------------------------
    for ri_id, (fid, name, qty) in ri.items():
        rule = categorize_ingredient(name)
        new = qty
        if rule is not None and rule.name in PIECE_CATEGORIES and qty > 0:
            pw = piece_weight(name)
            if pw is not None:
                if qty % 80 == 0:
                    new = (qty / 80) * pw
                elif qty % 8 == 0:
                    new = (qty / 8) * pw
        if new != qty:
            reason[ri_id] = "piece_weight"
            stats["pass1_piece_weight"] += 1
        corrected[ri_id] = new

    # --- Pass 2: clamp to the category max ------------------------------------
    for ri_id, (fid, name, _) in ri.items():
        rule = categorize_ingredient(name)
        if rule is None:
            continue  # no rule basis -- leave for a human, never auto-set
        if corrected[ri_id] > rule.max_g:
            corrected[ri_id] = float(rule.max_g)
            reason[ri_id] = "category_cap"
            stats["pass2_category_cap"] += 1

    # --- Pass 3: proportional dish scaling for dishes still over slot max ------
    by_dish: dict[str, list[str]] = defaultdict(list)
    for ri_id, (fid, _, _) in ri.items():
        by_dish[fid].append(ri_id)

    for fid, ids in by_dish.items():
        total = sum(corrected[i] for i in ids)
        max_total = DISH_TOTAL_MAX.get(slots.get(fid, ""), DISH_TOTAL_DEFAULT)
        if total <= max_total or total <= 0:
            continue
        scale = max_total / total
        for i in ids:
            corrected[i] = max(round(corrected[i] * scale, 1), 0.1)
            reason.setdefault(i, "dish_scale")
        stats["pass3_dishes_scaled"] += 1

    corrected = {k: round(v, 1) for k, v in corrected.items()}

    # --- Report ---------------------------------------------------------------
    changed = {k: v for k, v in corrected.items() if abs(v - ri[k][2]) >= 0.05}
    print(f"\n  pass 1 piece-weight corrections : {stats['pass1_piece_weight']:>6,}")
    print(f"  pass 2 category caps            : {stats['pass2_category_cap']:>6,}")
    print(f"  pass 3 dishes rescaled          : {stats['pass3_dishes_scaled']:>6,}")
    print(f"  rows differing from backup      : {len(changed):>6,}")

    def dish_totals(src) -> list[tuple[float, str]]:
        agg = defaultdict(float)
        for ri_id, (fid, _, _) in ri.items():
            agg[fid] += src(ri_id)
        return [(t, slots.get(f, "")) for f, t in agg.items()]

    for tag, src in (("backup", lambda i: ri[i][2]), ("rebuilt", lambda i: corrected[i])):
        tot = sorted(t for t, _ in dish_totals(src))
        ok = sum(1 for t, s in dish_totals(src) if t <= DISH_TOTAL_MAX.get(s, DISH_TOTAL_DEFAULT))
        small = sum(1 for t, _ in dish_totals(src) if t < 150)
        n = len(tot)
        print(f"  dish totals [{tag:7s}] median={tot[n // 2]:7.1f}g  "
              f"within slot max={100 * ok / n:5.1f}%  <150g={100 * small / n:5.1f}%")

    if args.dry_run:
        print("\n--dry-run: CSV not written.")
        return

    # --- Write into the review CSV -------------------------------------------
    rows = list(csv.DictReader(REVIEW_CSV.open(encoding="utf-8-sig")))
    fieldnames = list(rows[0].keys())
    written = 0
    for r in rows:
        rid = r["ri_id"]
        if rid in changed and abs(changed[rid] - float(r["quantity_g"])) >= 0.05:
            r["quantity_g_corrected"] = str(changed[rid])
            written += 1

    with REVIEW_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    print(f"\nWrote {written:,} quantity_g_corrected cells into {REVIEW_CSV}")
    print("Review in Excel, then:")
    print("  python -m scripts.import_recipe_ingredients_review "
          "data/review/recipe_ingredients_review.csv --dry-run")


if __name__ == "__main__":
    main()
