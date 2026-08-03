"""Smart match USDA SR against our ingredients — word-overlap approach."""
import json, os, sys, re
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))
from dotenv import load_dotenv; load_dotenv()
from sqlalchemy import create_engine, text

JSON_PATH = r"C:\Users\Lenovo\Desktop\Code\2026\Nutria\Mitihar_dietician\data\USDA_SR\FoodData_Central_sr_legacy_food_json_2021-10-28.json"

MACRO_IDS = {1008: "cal", 1003: "pro", 1005: "carb", 1004: "fat", 1079: "fib"}
STRIP_WORDS = {"raw", "dried", "fresh", "ground", "whole", "boiled", "cooked",
               "uncooked", "dry", "frozen", "canned", "roasted", "sliced", "chopped"}

def get_macros(food):
    m = {}
    for n in food.get("foodNutrients", []):
        nid = n.get("nutrient", {}).get("id")
        if nid in MACRO_IDS:
            m[MACRO_IDS[nid]] = n.get("amount", 0) or 0
    return m

def usda_primary(desc):
    """Take first comma-segment, lowercase, strip noise words."""
    primary = desc.split(",")[0].lower().strip()
    tokens = [w for w in re.split(r'\W+', primary) if w and w not in STRIP_WORDS]
    return " ".join(tokens)

def our_tokens(name):
    tokens = [w for w in re.split(r'\W+', name.lower().strip()) if w and w not in STRIP_WORDS]
    return set(tokens)

print("Loading USDA JSON...")
with open(JSON_PATH, encoding="utf-8") as f:
    data = json.load(f)
foods = data["SRLegacyFoods"]

# Category distribution
categories = {}
for food in foods:
    cat = food.get("foodCategory", {}).get("description", "Unknown")
    categories[cat] = categories.get(cat, 0) + 1
print(f"\nFood categories ({len(categories)} total):")
for cat, cnt in sorted(categories.items(), key=lambda x: -x[1])[:20]:
    print(f"  {cnt:4d}  {cat}")

# Build USDA lookup: primary_key → (food, macros)
# Prefer "raw" entries where there are duplicates
usda_map = {}
for food in foods:
    desc = food["description"]
    pkey = usda_primary(desc)
    if not pkey:
        continue
    macros = get_macros(food)
    if "cal" not in macros:
        continue
    # Prefer raw
    if pkey not in usda_map or "raw" in desc.lower():
        usda_map[pkey] = (desc, macros)

print(f"\nUSDA unique primary keys (post-normalization): {len(usda_map)}")

# Load our ingredients
engine = create_engine(os.environ["DATABASE_URL"].replace("+asyncpg", "+psycopg2"))
with engine.connect() as conn:
    our_rows = conn.execute(text("SELECT id, name, name_normalized FROM ingredients")).fetchall()

print(f"Our ingredients: {len(our_rows)}")

# Attempt match for each of our ingredients
matched = []    # (our_id, our_name, usda_desc, macros, strategy)
unmatched = []

for r in our_rows:
    our_name = r[1]
    our_norm = (r[2] or our_name).lower().strip()
    our_toks = our_tokens(our_name)
    if not our_toks:
        continue

    # Strategy 1: exact normalized name in usda_map
    if our_norm in usda_map:
        matched.append((r[0], our_name, usda_map[our_norm][0], usda_map[our_norm][1], "exact"))
        continue

    # Strategy 2: our_norm is exact key after removing words
    primary_stripped = " ".join(t for t in re.split(r'\W+', our_norm) if t not in STRIP_WORDS)
    if primary_stripped and primary_stripped in usda_map:
        matched.append((r[0], our_name, usda_map[primary_stripped][0], usda_map[primary_stripped][1], "stripped"))
        continue

    # Strategy 3: word-overlap — best USDA primary key that shares ALL our tokens
    best = None
    for pkey, (desc, macros) in usda_map.items():
        pkey_toks = set(pkey.split())
        if our_toks and our_toks.issubset(pkey_toks):
            best = (desc, macros, "subset")
            break
    if best:
        matched.append((r[0], our_name, best[0], best[1], best[2]))
        continue

    # Strategy 4: if we have a single token and it's in a USDA key as standalone word
    if len(our_toks) == 1:
        tok = list(our_toks)[0]
        if len(tok) >= 4:
            for pkey, (desc, macros) in usda_map.items():
                if tok in pkey.split():
                    best = (desc, macros, "single_word")
                    break
            if best:
                matched.append((r[0], our_name, best[0], best[1], best[2]))
                continue

    unmatched.append(our_name)

rate = len(matched) / len(our_rows) * 100
print(f"\n=== Match results ===")
print(f"Matched  : {len(matched)} / {len(our_rows)} ({rate:.1f}%)")
print(f"Unmatched: {len(unmatched)}")

by_strategy = {}
for m in matched:
    by_strategy[m[4]] = by_strategy.get(m[4], 0) + 1
print("By strategy:", by_strategy)

print("\nFirst 40 matches:")
for m in matched[:40]:
    macros = m[3]
    print(f"  [{m[4]}] '{m[1]}' → '{m[2][:45]}' | cal={macros.get('cal',0):.0f} pro={macros.get('pro',0):.1f}g")

print(f"\nFirst 20 unmatched:")
for name in unmatched[:20]:
    print(f"  {name}")

print(f"\n{'='*50}")
if rate >= 30:
    print(f"Match rate {rate:.1f}% >= 30% — OK to proceed with DB update")
else:
    print(f"Match rate {rate:.1f}% < 30% — ping before DB update")
