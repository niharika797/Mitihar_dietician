"""
Recipe Ingredients Sanity Check — Evidence-Based Thresholds
============================================================
Validates ~18k recipe_ingredients rows against limits derived from:
  • ICMR-NIN Dietary Guidelines for Indians 2024
  • FSSAI Eat Right India
  • WHO salt/sugar limits
  • IFCT 2017 food composition data
  • Standard Indian cooking practices

Usage:
    python scripts/sanity_check_ingredients.py
    python scripts/sanity_check_ingredients.py --csv path/to/file.csv
    python scripts/sanity_check_ingredients.py --from-db

Outputs:
    data/review/recipe_ingredients_flagged.csv  — every row with flag columns
    Console summary dashboard
"""

import argparse
import csv
import os
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# 1. Ingredient category definitions with evidence-based thresholds
# ---------------------------------------------------------------------------

@dataclass
class CategoryRule:
    """Defines a category with keywords and the max allowed quantity_g per serving."""
    name: str
    keywords: list[str]
    max_g: float
    warn_g: float  # softer warning threshold
    evidence: str   # short citation


CATEGORY_RULES: list[CategoryRule] = [
    # --- Cereals & Grains ---
    CategoryRule(
        name="cereal_grain",
        keywords=[
            "rice", "flour", "wheat", "ragi", "bajra", "jowar", "maize",
            "oats", "vermicelli", "semiya", "sooji", "semoila", "atta",
            "bread", "pav", "roti", "maida",
            # regional / prepared-cereal names seen in the 6k dataset
            "poha", "batter", "idli", "dosa",
            "quinoa", "sabudana", "semolina", "semia", "millet", "barley",
            "macaroni", "couscous", "polenta", "oatmeal", "phulka", "papad",
            "tortillas", "phyllo sheets", "boondi", "sev", "papdi puris",
            "pani puris", "khichdi", "medu vada", "khaman dhokla", "badi",
            "bhujia", "samosa",
        ],
        max_g=120, warn_g=90,
        evidence="ICMR 2024: 250g cereals/day; katori standard 60-80g per serving",
    ),
    # --- Pulses & Legumes ---
    CategoryRule(
        name="pulse_legume",
        keywords=[
            "dal", "gram", "chana", "moong", "masoor", "rajma", "lentil",
            "kidney bean", "chickpea", "pigeon pea", "bengal gram",
            "black gram", "green gram", "red gram", "tur", "urad",
            "soyabean", "soya chunk", "mothbean", "black eye bean",
            "yellow peas",
            "cowpea", "soy chunks", "soy granules", "soya chaap", "green mung",
            "mixed sprouts", "moth sprouts", "pigeonpea", "jackfruit seeds",
            # regional dried-lentil preparations (Rajasthani/Nepali)
            "rabodi", "masaura", "channa sprouts", "horse gram",
        ],
        max_g=90, warn_g=60,
        evidence="ICMR 2024: 85g pulses/day total",
    ),
    # --- Vegetables ---
    CategoryRule(
        name="vegetable",
        keywords=[
            "potato", "onion", "tomato", "cauliflower", "spinach", "palak",
            "brinjal", "eggplant", "peas", "carrot", "beans", "capsicum",
            "cabbage", "gourd", "pumpkin", "drumstick", "radish", "raddish",
            "cucumber", "beetroot", "corn", "mushroom", "lady finger",
            "bhindi", "banana flower", "yam", "chayote",
            "fenugreek leaves", "mustard leaves",
            # Hindi/regional names + variants missing from the original list
            "bell pepper", "broccoli", "shallot", "colocasia", "karela",
            "kaddu", "mooli", "mullangi", "methi leaves", "arbi", "tinda",
            "tindora", "gawar phali", "gwar pods", "suran", "chow chow",
            "parwal", "okra", "vellai poosanikai", "chakundar", "avarekai",
            "lotus stem", "plantain stem", "kohl rabi", "zucchini", "kale",
            "brussel sprouts", "gobi", "tapioca root", "taro root",
            "jackfruit raw", "sundakkai", "sundkai", "trumpet", "celery",
            "dill leaves", "fenugreek", "neem leaves", "mixed vegetables",
            "olives", "cowpea pod", "gunde", "pirandai",
        ],
        max_g=300, warn_g=200,
        evidence="ICMR 2024: 400g vegetables/day total; single sabzi ~150-200g",
    ),
    # --- Oil & Fat ---
    CategoryRule(
        name="oil_fat",
        # Explicit "<seed> oil" entries are required: bare "oil" (3 chars) loses the
        # longest-keyword match to "coconut"/"sesame"/"mustard", which would file
        # cooking oils under nut_seed/powder_spice and cap them at the wrong limit.
        keywords=[
            "oil", "ghee", "butter", "vanaspati",
            "mustard oil", "coconut oil", "sesame oil",
        ],
        max_g=20, warn_g=15,
        evidence="ICMR 2024: 27g visible fat/day; FSSAI: 15-20g oil/day",
    ),
    # --- Dairy: Curd/Yoghurt ---
    CategoryRule(
        name="dairy_curd",
        # "buttermilk" must outrank oil_fat's "butter" and dairy_milk's "milk"
        keywords=["curd", "yoghurt", "yogurt", "dahi", "chaas", "lassi", "buttermilk"],
        max_g=200, warn_g=150,
        evidence="ICMR 2024: 300ml milk-curd/day; generous raita ~150g",
    ),
    # --- Dairy: Milk ---
    CategoryRule(
        name="dairy_milk",
        keywords=["milk", "coconut milk"],
        max_g=200, warn_g=150,
        evidence="ICMR 2024: 300ml dairy/day",
    ),
    # --- Dairy: Paneer/Cheese ---
    CategoryRule(
        name="dairy_paneer",
        keywords=["paneer", "cheese", "cottage cheese", "tofu", "khoya"],
        max_g=150, warn_g=100,
        evidence="NIN: 50-100g paneer/serving standard; 150g extreme upper",
    ),
    # --- Dairy: Cream ---
    CategoryRule(
        name="dairy_cream",
        keywords=["cream", "fresh cream", "malai"],
        max_g=50, warn_g=30,
        evidence="High-fat; small amounts used for richness",
    ),
    # --- Meat & Fish ---
    CategoryRule(
        name="meat_fish",
        keywords=[
            "chicken", "mutton", "pork", "fish", "prawns", "lamb",
            "rohu", "pomfret", "berma",
            "shrimp", "crab", "clams", "parshe", "aar maach",
        ],
        max_g=150, warn_g=100,
        evidence="ICMR: 80g meat replaces 30g pulses; IDA standard 60-80g/serving",
    ),
    # --- Eggs ---
    CategoryRule(
        name="egg",
        keywords=["egg"],
        max_g=100, warn_g=60,
        evidence="1 egg edible portion = 50g (BASU grading); max 2 per serving",
    ),
    # --- Nuts & Seeds ---
    CategoryRule(
        name="nut_seed",
        keywords=[
            "almond", "cashew", "peanut", "walnut", "chia", "flax",
            "sesame", "poppy seed", "coconut fresh", "coconut dry",
            "coconut", "makhana",
            "badam", "pistachio", "mixed nuts", "melon seeds", "khuskhus",
            "khus khus", "groundnut", "pecan", "sabza seeds", "dry poppy",
            "poppy poppy", "gond",
        ],
        max_g=60, warn_g=35,
        evidence="ICMR 2024: 30-45g nuts-seeds/day total",
    ),
    # --- Sugar & Sweeteners ---
    CategoryRule(
        name="sugar_sweet",
        keywords=["sugar", "jaggery", "honey", "syrup", "mishri"],
        max_g=30, warn_g=15,
        evidence="ICMR 2024 + WHO: <25-30g added sugar/day",
    ),
    # --- Whole Spices ---
    CategoryRule(
        name="whole_spice",
        keywords=[
            "bay leaf", "cardamom", "clove", "cinnamon", "star anise",
            "whole pepper", "black pepper", "mace", "nutmeg",
            "fennel seeds", "mustard seeds", "cumin seeds", "ajwain",
            "methi seeds", "fenugreek seed",
            # plural/Hindi variants: "long" = laung = clove, "rye" = rai = mustard seed
            "bay leaves", "long", "rye", "kalonji",
            "fennel", "kala jeera", "lavang", "aniseed", "chakra flowers",
            "kalpasi", "edible camphor",
            # Tamil long-pepper medicinals, used by the pinch in rasam
            "thipli", "kandathipli", "arisithipli",
        ],
        max_g=5, warn_g=3,
        evidence="Bay leaf ~0.5g/piece, cardamom ~0.2g/pod, clove ~0.01g each",
    ),
    # --- Powdered Spices ---
    CategoryRule(
        name="powder_spice",
        keywords=[
            "turmeric", "chilli powder", "red chilli powder",
            "cumin powder", "coriander powder",
            "garam masala", "sambar powder", "biryani masala",
            "masala powder", "amchur", "asafoetida",
            # US spelling + bare forms + blends (longer keywords above still win)
            "chili powder", "red chili powder", "rasam powder",
            "panch phoran", "kasuri methi", "cumin", "mustard",
            "anardana powder", "pepper powder", "paprika", "methi powder",
            "fennel powder", "amchoor", "groundnut powder", "vangi bath powder",
            "goda masala", "tandoori masala", "achari masala", "panchon masala",
            "curry powder", "all spice powder", "cajun spice mix", "meat masala",
            "pizza seasoning", "bhat powder", "bhat spice powder",
            "puliodarai powder", "fenugreek powder", "kasoori methi",
            "kasoori fenugreek", "cocoa powder", "coffee powder",
            "panch four masala", "mixed herbs", "dried oregano", "fresh oregano",
            "baking soda", "cooking soda", "baking powder", "active dry yeast",
        ],
        max_g=10, warn_g=5,
        evidence="Typical usage 1-3g per spice per serving",
    ),
    # --- Curry Leaves (tempering only — never a bulk ingredient) ---
    # Split out of fresh_herb: the flat 30g herb limit let 25g curry-leaf rows
    # (~125-250 leaves) pass silently. Research SS3K puts tempering at 1-2g.
    CategoryRule(
        name="curry_leaf",
        keywords=["curry leaves", "curry leaf", "kadhi leaves", "kadi leaves"],
        max_g=5, warn_g=2,
        evidence="IFCT 2017: 0.1-0.2g/leaf; one tempering = 8-15 leaves = 1-2g",
    ),
    # --- Fresh Herbs (tempering to chutney) ---
    CategoryRule(
        name="fresh_herb",
        keywords=[
            "coriander leaves", "corriander", "coriander",
            "mint leaves", "basil",
            "parsley leaves", "peppermint", "tulsi", "mint", "thyme leaves",
            "gongura leaves", "brahmi leaves", "indian borage",
            "kaffir lime leaves", "tea leaves", "tea leaf",
            "hibiscus leaves", "neem flowers", "rose petals",
        ],
        max_g=30, warn_g=10,
        evidence="Coriander/mint: handful 5-10g; chutney up to 30g",
    ),
    # --- Aromatics (chilli, garlic, ginger) ---
    CategoryRule(
        name="aromatic",
        keywords=[
            "green chilli", "green chillies", "dry red chilli",
            "dry red chillies", "red chillies",
            "garlic", "cloves garlic", "ginger",
            "chilli", "green chilli",
            # US "chili" spelling — 116 rows were uncategorized without these
            "chili", "green chili", "green chilies",
            "dry red chili", "dry red chilies", "red chili", "red chilies",
            # sun-dried South Indian chilli/berry preparations -- fried by the
            # piece as a tempering, never a bulk ingredient
            "mor milagai", "milagai", "vathal", "sundakkai vathal",
        ],
        max_g=25, warn_g=15,
        evidence="Green chilli: 2-5g/piece; garlic clove: 3-7g; ginger inch: 5-10g",
    ),
    # --- Saffron ---
    CategoryRule(
        name="saffron",
        keywords=["saffron", "kesar"],
        max_g=2, warn_g=0.5,
        evidence="Culinary: 3 strands/serving = 0.02g; toxic at >=5g",
    ),
    # --- Fruit ---
    CategoryRule(
        name="fruit",
        keywords=[
            "banana", "apple", "orange", "grape", "pomegranate",
            "pomogranate", "strawberry", "starwberry", "pineapple",
            "mango", "papaya", "guava", "watermelon", "lemon",
            "tamarind", "imli", "mix berries",
            "raisin", "dates", "amla", "kokum", "strawberries", "blackberries",
            "blueberries", "jamun", "cranberries", "figs", "hog plum", "falsa",
            "mixed fruits", "aamras", "avocado", "jackfruit ripe", "gulkand",
        ],
        max_g=150, warn_g=100,
        evidence="ICMR 2024: 100g fruit/day; generous serving ~100-150g",
    ),
    # --- Leafy Greens (as main ingredient, not herb) ---
    CategoryRule(
        name="leafy_green",
        keywords=[
            "agathi", "keerai", "amaranth", "moringa",
        ],
        max_g=150, warn_g=100,
        evidence="ICMR: 100g leafy greens/day; these wilt significantly",
    ),
    # --- Prepared condiments, sauces, pickles, essences ---
    # Served alongside rather than cooked in; a portion is a spoonful, not a bowl.
    CategoryRule(
        name="condiment_sauce",
        keywords=[
            "chutney", "pickle", "achar", "sauce", "vinegar", "vinaigrette",
            "mayo", "essence", "extract", "curry paste", "spread", "ketchup",
            "dip", "gulkand",
        ],
        max_g=30, warn_g=20,
        evidence="IDA: condiment portion 15-30g; FSSAI salt/sugar limits bind these",
    ),
    # --- Beverage / liquid bases (water-weight, near-zero energy density) ---
    CategoryRule(
        name="beverage_liquid",
        keywords=[
            "tea", "coffee", "ice", "stock", "broth", "soda", "juice",
            "water", "kadha",
        ],
        max_g=300, warn_g=250,
        evidence="Standard cup/glass 200-250ml; mostly water, negligible energy",
    ),
]

# Items that are NOT eaten but were ingested as ingredient rows with a real
# quantity_g -- they inflate dish weight and calories for food nobody consumes.
# These must be DELETED from recipe_ingredients, not capped: there is no correct
# gram value for a toothpick. Kept separate from the category rules on purpose,
# so nothing here can ever be silently auto-corrected into a plausible number.
NON_FOOD_NAMES = {
    "coal", "charcoal", "toothpicks", "toothpick",
}

# Name fragments left behind by the recipe-text parser -- not ingredients.
# Matched on the WHOLE name (exact, case-insensitive) so real ingredients
# containing these words are unaffected.
PARSE_GARBAGE_NAMES = {
    "green", "save", "good", "mess", "spoon", "leaf", "curry", "horse",
    "1/2", "hung", "of casmis", "arabic",
}

# Slot-type based total dish weight thresholds
DISH_TOTAL_MAX = {
    "condiment": 350,
    "accompaniment": 350,
    "beverage": 350,
    "main_dish": 500,
    "sabzi": 500,
    "dal_protein": 500,
    "grain": 500,
    "snack_item": 500,
    "one_pot": 650,
}
DISH_TOTAL_DEFAULT = 500


# ---------------------------------------------------------------------------
# 2. Ingredient categorizer
# ---------------------------------------------------------------------------

def categorize_ingredient(name: str) -> Optional[CategoryRule]:
    """Match an ingredient name to a category using keyword matching.
    Returns the MOST SPECIFIC match (longest keyword match wins)."""
    name_lower = name.lower().strip()

    best_match: Optional[CategoryRule] = None
    best_keyword_len = 0

    for rule in CATEGORY_RULES:
        for kw in rule.keywords:
            if kw in name_lower and len(kw) > best_keyword_len:
                best_match = rule
                best_keyword_len = len(kw)

    return best_match


# ---------------------------------------------------------------------------
# 3. Flag definitions
# ---------------------------------------------------------------------------

@dataclass
class Flag:
    severity: str  # "ERROR" or "WARN"
    check: str     # check name
    message: str   # human-readable explanation


@dataclass
class RowResult:
    """Result of checking a single row."""
    row: dict
    category: str
    flags: list[Flag] = field(default_factory=list)

    @property
    def has_error(self) -> bool:
        return any(f.severity == "ERROR" for f in self.flags)

    @property
    def has_warn(self) -> bool:
        return any(f.severity == "WARN" for f in self.flags)


def safe_float(val: str, default: float = 0.0) -> float:
    """Safely convert a string to float."""
    if not val:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


# ---------------------------------------------------------------------------
# 4. Check functions
# ---------------------------------------------------------------------------

def check_per_ingredient_max(row: dict, rule: Optional[CategoryRule]) -> list[Flag]:
    """Check 1: Is this ingredient's quantity within its category max?"""
    flags = []
    val_str = row.get("quantity_g", "").strip()
    if not val_str:
        flags.append(Flag("ERROR", "missing_quantity", f"Ingredient '{row['ingredient_name']}' has empty/missing quantity_g"))
        return flags

    try:
        qty = float(val_str)
    except ValueError:
        flags.append(Flag("ERROR", "invalid_quantity", f"Ingredient '{row['ingredient_name']}' has non-numeric quantity_g: '{val_str}'"))
        return flags

    if qty <= 0:
        flags.append(Flag("WARN", "zero_or_negative_qty", f"Ingredient '{row['ingredient_name']}' has non-positive quantity_g: {qty}"))
        return flags

    if rule is None:
        if qty > 200:
            flags.append(Flag(
                "WARN", "uncategorized_high_qty",
                f"Uncategorized ingredient '{row['ingredient_name']}' with {qty}g -- manual review needed"
            ))
        return flags

    if qty > rule.max_g:
        flags.append(Flag(
            "ERROR", "exceeds_max",
            f"{row['ingredient_name']} ({qty}g) exceeds {rule.name} max of {rule.max_g}g. "
            f"Evidence: {rule.evidence}"
        ))
    elif qty > rule.warn_g:
        flags.append(Flag(
            "WARN", "near_max",
            f"{row['ingredient_name']} ({qty}g) is high for {rule.name} "
            f"(warn at {rule.warn_g}g, max {rule.max_g}g)"
        ))

    return flags


def check_count_vs_grams(row: dict) -> list[Flag]:
    """Check 2: Detect the systematic count-as-grams parsing bug.
    Pattern: values like 160, 240, 320, 640, 800 for items that should be <5g."""
    flags = []
    qty = safe_float(row.get("quantity_g", ""))
    name_lower = row["ingredient_name"].lower()

    # Items that are typically counted, not weighed, and should be <10g per serving
    COUNT_ITEMS = {
        "curry leaves": 5,      # max sensible grams
        "bay leaf": 2,
        "cardamom": 3,
        "black cardamom": 5,
        "clove": 2,
        "green chilli": 20,
        "green chillies": 20,
        "dry red chilli": 10,
        "dry red chillies": 10,
        "red chillies": 10,
        "cloves garlic": 25,
    }

    # Longest keyword wins, same rule as categorize_ingredient(). Iterating in
    # dict order instead would let "clove" (max 2g) match "Cloves garlic" and
    # flag correct 15g garlic rows as parsing bugs -- the same keyword collision
    # that made the deprecated fix_ingredient_quantities.py crush garlic to 1.0g.
    best_kw: Optional[str] = None
    best_max = 0.0
    for item_kw, max_sensible in COUNT_ITEMS.items():
        if item_kw in name_lower and len(item_kw) > len(best_kw or ""):
            best_kw, best_max = item_kw, max_sensible

    if best_kw is not None and qty > best_max * 3:
        # qty is > 3x the already-generous max -- almost certainly a parsing bug
        flags.append(Flag(
            "ERROR", "count_as_grams",
            f"LIKELY PARSING BUG: '{row['ingredient_name']}' at {qty}g -- "
            f"probable count misparsed as grams (sensible max: {best_max}g). "
            f"E.g., '8 curry leaves' -> 640g instead of ~1.5g"
        ))

    return flags


def check_egg_count(row: dict) -> list[Flag]:
    """Check 3: Detect eggs stored as count instead of grams.
    Pattern: quantity_g == 1, 2, 3 for eggs (should be 50g per egg)."""
    flags = []
    name_lower = row["ingredient_name"].lower()
    qty = safe_float(row.get("quantity_g", ""))

    if "egg" in name_lower and qty <= 10:
        flags.append(Flag(
            "WARN", "egg_count_not_grams",
            f"'{row['ingredient_name']}' has quantity_g={qty} -- likely a count, not grams. "
            f"1 egg edible portion ~ 50g (BASU India grading). Should be {qty * 50}g?"
        ))

    return flags


def check_not_food(row: dict) -> list[Flag]:
    """Check 6: rows that are not food at all, or are parser debris.

    Both need a human to DELETE the row -- capping them to a category max would
    just turn an obviously-wrong number into a plausible-looking wrong number.
    """
    name = row["ingredient_name"].strip().lower()
    qty = safe_float(row.get("quantity_g", ""))

    if name in NON_FOOD_NAMES:
        return [Flag(
            "ERROR", "not_food",
            f"'{row['ingredient_name']}' ({qty}g) is not edible -- used for the dhungar "
            f"smoking technique or as equipment. DELETE this row; it adds phantom "
            f"weight and calories to the dish."
        )]

    if name in PARSE_GARBAGE_NAMES:
        return [Flag(
            "ERROR", "parse_garbage",
            f"'{row['ingredient_name']}' ({qty}g) is a fragment left by the recipe-text "
            f"parser, not an ingredient. DELETE this row (the real ingredient is usually "
            f"already present in the same dish)."
        )]

    return []


def check_dish_total(dish_rows: list[dict]) -> list[Flag]:
    """Check 4: Is the total raw weight of all ingredients in a dish reasonable?"""
    flags = []
    if not dish_rows:
        return flags

    total_g = sum(safe_float(r.get("quantity_g", "")) for r in dish_rows)
    slot_type = dish_rows[0].get("slot_type", "")
    max_total = DISH_TOTAL_MAX.get(slot_type, DISH_TOTAL_DEFAULT)

    if total_g > max_total * 2:
        flags.append(Flag(
            "ERROR", "dish_total_extreme",
            f"Dish total {total_g:.0f}g is >{max_total * 2}g "
            f"(2x the max for slot_type='{slot_type}'). "
            f"Almost certainly multi-serving data or parsing errors. "
            f"Evidence: Indian thali total ~500-650g (all items)"
        ))
    elif total_g > max_total:
        flags.append(Flag(
            "WARN", "dish_total_high",
            f"Dish total {total_g:.0f}g exceeds {max_total}g limit "
            f"for slot_type='{slot_type}'"
        ))

    return flags


def check_statistical_outlier(
    row: dict, ingredient_stats: dict[str, dict]
) -> list[Flag]:
    """Check 5: Flag if quantity_g is a statistical outlier for this ingredient.
    Uses IQR method: outlier if > Q3 + 3*IQR."""
    flags = []
    name = row["ingredient_name"].strip()
    qty = safe_float(row.get("quantity_g", ""))

    stats = ingredient_stats.get(name)
    if stats is None or stats["count"] < 5:
        return flags  # not enough data for statistics

    upper_fence = stats["q3"] + 3 * stats["iqr"]
    if upper_fence > 0 and qty > upper_fence:
        flags.append(Flag(
            "WARN", "statistical_outlier",
            f"'{name}' at {qty}g is a statistical outlier. "
            f"Median={stats['median']:.1f}g, Q3={stats['q3']:.1f}g, "
            f"upper fence={upper_fence:.1f}g (Q3+3xIQR). "
            f"Seen {stats['count']} times across all recipes."
        ))

    return flags


# ---------------------------------------------------------------------------
# 5. Statistics computation
# ---------------------------------------------------------------------------

def compute_ingredient_stats(rows: list[dict]) -> dict[str, dict]:
    """Compute median, Q1, Q3, IQR for each ingredient name."""
    from statistics import median, quantiles

    by_name: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        val = safe_float(r.get("quantity_g", ""))
        if val > 0:
            by_name[r["ingredient_name"].strip()].append(val)

    stats = {}
    for name, values in by_name.items():
        values.sort()
        n = len(values)
        if n < 4:
            med = median(values)
            stats[name] = {
                "count": n, "median": med,
                "q1": med, "q3": med, "iqr": 0,
            }
        else:
            q = quantiles(values, n=4)
            q1, med_val, q3 = q[0], q[1], q[2]
            stats[name] = {
                "count": n, "median": med_val,
                "q1": q1, "q3": q3, "iqr": q3 - q1,
            }

    return stats


# ---------------------------------------------------------------------------
# 6. Main pipeline
# ---------------------------------------------------------------------------

def load_csv(path: str) -> list[dict]:
    """Load recipe_ingredients_audit.csv."""
    rows = []
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def run_checks(rows: list[dict]) -> tuple[list[RowResult], list[tuple[str, str, list[Flag]]]]:
    """Run all checks. Returns (per-row results, per-dish flags)."""

    # Pre-compute ingredient statistics
    ing_stats = compute_ingredient_stats(rows)

    # Group by dish_id for dish-level checks
    by_dish: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_dish[r["dish_id"]].append(r)

    # Per-row checks
    results: list[RowResult] = []
    for r in rows:
        rule = categorize_ingredient(r["ingredient_name"])
        cat_name = rule.name if rule else "uncategorized"

        all_flags = []
        all_flags.extend(check_per_ingredient_max(r, rule))
        all_flags.extend(check_count_vs_grams(r))
        all_flags.extend(check_egg_count(r))
        all_flags.extend(check_statistical_outlier(r, ing_stats))
        all_flags.extend(check_not_food(r))

        results.append(RowResult(row=r, category=cat_name, flags=all_flags))

    # Per-dish checks
    dish_flags: list[tuple[str, str, list[Flag]]] = []
    for dish_id, dish_rows in by_dish.items():
        dish_name = dish_rows[0]["dish_name"]
        d_flags = check_dish_total(dish_rows)
        if d_flags:
            dish_flags.append((dish_id, dish_name, d_flags))

    return results, dish_flags


def write_flagged_csv(
    results: list[RowResult],
    dish_flags_map: dict[str, list[Flag]],
    output_path: str,
):
    """Write every row to a CSV with additional flag columns."""
    fieldnames = [
        "dish_id", "dish_name", "slot_type", "is_verified",
        "ingredient_name", "quantity_g",
        "category", "severity", "check", "message", "dish_level_flag",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for res in results:
            dish_flag_msgs = ""
            d_flags = dish_flags_map.get(res.row["dish_id"], [])
            if d_flags:
                dish_flag_msgs = " | ".join(fl.message for fl in d_flags)

            if res.flags:
                for flag in res.flags:
                    writer.writerow({
                        **res.row,
                        "category": res.category,
                        "severity": flag.severity,
                        "check": flag.check,
                        "message": flag.message,
                        "dish_level_flag": dish_flag_msgs,
                    })
            else:
                writer.writerow({
                    **res.row,
                    "category": res.category,
                    "severity": "OK",
                    "check": "",
                    "message": "",
                    "dish_level_flag": dish_flag_msgs,
                })


def print_dashboard(
    results: list[RowResult],
    dish_flags: list[tuple[str, str, list[Flag]]],
    total_rows: int,
):
    """Print a summary dashboard to console."""
    errors = [r for r in results if r.has_error]
    warns = [r for r in results if r.has_warn and not r.has_error]
    clean = [r for r in results if not r.flags]

    print("\n" + "=" * 72)
    print("  RECIPE INGREDIENTS SANITY CHECK -- EVIDENCE-BASED THRESHOLDS")
    print("  Sources: ICMR-NIN 2024, FSSAI, WHO, IFCT 2017")
    print("=" * 72)

    print(f"\n  Total rows checked:    {total_rows:,}")
    print(f"  Clean (no flags):      {len(clean):,} ({len(clean)*100/total_rows:.1f}%)")
    print(f"  Warnings:              {len(warns):,} ({len(warns)*100/total_rows:.1f}%)")
    print(f"  Errors:                {len(errors):,} ({len(errors)*100/total_rows:.1f}%)")

    # Break down errors by check type
    error_by_check: dict[str, int] = defaultdict(int)
    for r in results:
        for f in r.flags:
            if f.severity == "ERROR":
                error_by_check[f.check] += 1

    if error_by_check:
        print(f"\n  {'_' * 60}")
        print("  ERROR breakdown by check type:")
        print(f"  {'_' * 60}")
        for check, count in sorted(error_by_check.items(), key=lambda x: -x[1]):
            print(f"    {check:30s}  {count:5d} rows")

    warn_by_check: dict[str, int] = defaultdict(int)
    for r in results:
        for f in r.flags:
            if f.severity == "WARN":
                warn_by_check[f.check] += 1

    if warn_by_check:
        print(f"\n  {'_' * 60}")
        print("  WARNING breakdown by check type:")
        print(f"  {'_' * 60}")
        for check, count in sorted(warn_by_check.items(), key=lambda x: -x[1]):
            print(f"    {check:30s}  {count:5d} rows")

    # Dish-level flags
    dish_errors = [d for d in dish_flags if any(f.severity == "ERROR" for f in d[2])]
    dish_warns = [d for d in dish_flags if any(f.severity == "WARN" for f in d[2]) and d not in dish_errors]

    print(f"\n  {'_' * 60}")
    print("  Dish-level total weight checks:")
    print(f"  {'_' * 60}")
    print(f"    Dishes with ERROR (extreme weight):  {len(dish_errors)}")
    print(f"    Dishes with WARN  (high weight):     {len(dish_warns)}")

    # Top 15 worst offenders
    if errors:
        print(f"\n  {'_' * 60}")
        print("  Top 15 worst offenders (by quantity_g):")
        print(f"  {'_' * 60}")
        sorted_errors = sorted(errors, key=lambda r: safe_float(r.row.get("quantity_g", "")), reverse=True)
        for r in sorted_errors[:15]:
            qty = safe_float(r.row.get("quantity_g", ""))
            flag_msg = r.flags[0].message[:80] if r.flags else ""
            print(
                f"    dish={r.row['dish_id']:>5s} | "
                f"{r.row['ingredient_name'][:30]:30s} | "
                f"{qty:>8.1f}g | {flag_msg}"
            )

    # Top 10 dishes by total weight
    if dish_errors:
        print(f"\n  {'_' * 60}")
        print("  Top 10 heaviest dishes:")
        print(f"  {'_' * 60}")
        for dish_id, dish_name, flags in sorted(
            dish_errors,
            key=lambda x: float(x[2][0].message.split("g")[0].split()[-1]) if x[2] else 0,
            reverse=True,
        )[:10]:
            msg = flags[0].message[:70] if flags else ""
            print(f"    dish={dish_id:>5s} | {dish_name[:35]:35s} | {msg}")

    # Category distribution
    cat_counts: dict[str, int] = defaultdict(int)
    for r in results:
        cat_counts[r.category] += 1

    print(f"\n  {'_' * 60}")
    print("  Category distribution:")
    print(f"  {'_' * 60}")
    for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
        pct = count * 100 / total_rows
        err_in_cat = sum(1 for r in results if r.category == cat and r.has_error)
        status = f" ({err_in_cat} errors)" if err_in_cat else ""
        print(f"    {cat:25s}  {count:5d} ({pct:5.1f}%){status}")

    print(f"\n{'=' * 72}")
    print()


# ---------------------------------------------------------------------------
# 7. DB loader (optional, for --from-db mode)
# ---------------------------------------------------------------------------

def load_from_db() -> list[dict]:
    """Load directly from PostgreSQL via SQLAlchemy (sync)."""
    sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))
    from dotenv import load_dotenv
    load_dotenv()
    from sqlalchemy import create_engine, text

    db_url = os.environ["DATABASE_URL"].replace("+asyncpg", "+psycopg2")
    engine = create_engine(db_url)

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                fi.id AS dish_id,
                fi.recipe_name AS dish_name,
                fi.slot_type,
                fi.is_verified,
                ing.name AS ingredient_name,
                ri.quantity_g
            FROM recipe_ingredients ri
            JOIN food_items fi ON fi.id = ri.food_item_id
            JOIN ingredients ing ON ing.id = ri.ingredient_id
            ORDER BY fi.id, ri.id
        """))
        rows = []
        for r in result.fetchall():
            rows.append({
                "dish_id": str(r[0]),
                "dish_name": r[1],
                "slot_type": r[2] or "",
                "is_verified": str(r[3]),
                "ingredient_name": r[4],
                "quantity_g": str(float(r[5])),
            })
    return rows


# ---------------------------------------------------------------------------
# 8. Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Evidence-based sanity check for recipe_ingredients data"
    )
    parser.add_argument(
        "--csv", default=None,
        help="Path to data/review/recipe_ingredients_audit.csv (default: auto-detect)"
    )
    parser.add_argument(
        "--from-db", action="store_true",
        help="Load data directly from PostgreSQL instead of CSV"
    )
    parser.add_argument(
        "--output", default=None,
        help="Output CSV path (default: data/review/recipe_ingredients_flagged.csv)"
    )
    args = parser.parse_args()

    # Load data
    if args.from_db:
        print("Loading from database...")
        rows = load_from_db()
    else:
        csv_path = args.csv
        if csv_path is None:
            # Auto-detect CSV in data/review/
            project_root = Path(__file__).resolve().parent.parent
            csv_path = project_root / "data" / "review" / "recipe_ingredients_audit.csv"
        print(f"Loading from {csv_path}...")
        rows = load_csv(str(csv_path))

    print(f"Loaded {len(rows):,} rows.")

    # Run checks
    results, dish_flags = run_checks(rows)

    # Build dish flags lookup
    dish_flags_map: dict[str, list[Flag]] = {}
    for dish_id, _, flags in dish_flags:
        dish_flags_map[dish_id] = flags

    # Output
    output_path = args.output
    if output_path is None:
        project_root = Path(__file__).resolve().parent.parent
        output_path = project_root / "data" / "review" / "recipe_ingredients_flagged.csv"

    write_flagged_csv(results, dish_flags_map, str(output_path))
    print(f"Flagged CSV written to: {output_path}")

    # Dashboard
    print_dashboard(results, dish_flags, len(rows))


if __name__ == "__main__":
    main()
