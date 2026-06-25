"""Explore USDA SR Legacy JSON structure."""
import json, os, sys
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))
from dotenv import load_dotenv; load_dotenv()
from sqlalchemy import create_engine, text

JSON_PATH = r"C:\Users\Lenovo\Desktop\Code\2026\Nutria\Mitihar_dietician\data\USDA_SR\FoodData_Central_sr_legacy_food_json_2021-10-28.json"

print("Loading JSON (210MB, may take a moment)...")
with open(JSON_PATH, encoding="utf-8") as f:
    data = json.load(f)

# Top-level keys
print("Top-level keys:", list(data.keys()))

foods = data.get("SRLegacyFoods") or data.get("Foods") or list(data.values())[0]
print(f"Total foods: {len(foods)}")

# First food structure
f0 = foods[0]
print("\nFirst food keys:", list(f0.keys()))
print("First food description:", f0.get("description"))

# Nutrient structure
nutrients = f0.get("foodNutrients", [])
print(f"\nNutrients in first food ({len(nutrients)} total), first 10:")
for n in nutrients[:10]:
    nut = n.get("nutrient", {})
    print(f"  id={nut.get('id')} name='{nut.get('name')}' unit={nut.get('unitName')} amount={n.get('amount')}")

# Find the nutrient IDs for our 5 macros
MACRO_IDS = {1008: "energy_kcal", 1003: "protein_g", 1005: "carbs_g", 1004: "fat_g", 1079: "fiber_g"}
print("\nSearching for macro nutrient IDs in first food:")
for n in nutrients:
    nut_id = n.get("nutrient", {}).get("id")
    if nut_id in MACRO_IDS:
        print(f"  {MACRO_IDS[nut_id]}: {n.get('amount')}")

# Sample food names
print(f"\nFirst 20 food descriptions:")
for food in foods[:20]:
    print(f"  {food['description']}")

# Check foodCategory
if "foodCategory" in f0:
    print(f"\nfoodCategory example: {f0['foodCategory']}")

# Pre-match against our ingredients
def normalize(s):
    return str(s).lower().strip()

engine = create_engine(os.environ["DATABASE_URL"].replace("+asyncpg", "+psycopg2"))
with engine.connect() as conn:
    our_rows = conn.execute(text("SELECT id, name, name_normalized FROM ingredients")).fetchall()

our_norms = {}
for r in our_rows:
    key = r[2] if r[2] else normalize(r[1])
    our_norms[key] = r[0]

usda_norms = {normalize(f["description"]): f for f in foods}

# Exact match
exact = [(k, our_norms[k]) for k in usda_norms if k in our_norms]
print(f"\nExact match: {len(exact)} / {len(foods)} ({len(exact)/len(foods)*100:.1f}%)")
print("Matched names (first 30):")
for name, our_id in exact[:30]:
    print(f"  '{name}'")
