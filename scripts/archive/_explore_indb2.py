"""Deep-dive INDB structure and pre-check match rate against our ingredients."""
import os, sys
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))
from dotenv import load_dotenv; load_dotenv()

import pandas as pd
from sqlalchemy import create_engine, text

INDB_PATH = r"C:\Users\Lenovo\Desktop\Code\2026\Nutria\Mitihar_dietician\data\INDB\Indian-Nutrient-Databank-INDB--main\INDB.xlsx"

df = pd.read_excel(INDB_PATH, sheet_name="Nutrient Data")

# Sources
print("=== primarysource breakdown ===")
print(df["primarysource"].value_counts().to_string())

# Sample food names
print("\n=== First 20 food_names ===")
for n in df["food_name"].head(20):
    print(f"  {n}")

print("\n=== Last 20 food_names ===")
for n in df["food_name"].tail(20):
    print(f"  {n}")

# Nutrition value ranges
print("\n=== Nutrition ranges (should be per 100g) ===")
for col in ["energy_kcal", "protein_g", "carb_g", "fat_g", "fibre_g"]:
    s = df[col].dropna()
    print(f"  {col}: min={s.min():.1f}  max={s.max():.1f}  mean={s.mean():.1f}")

# Exact match check against our DB
def normalize(s):
    return str(s).lower().strip() if s else ""

df["name_norm"] = df["food_name"].apply(normalize)

engine = create_engine(os.environ["DATABASE_URL"].replace("+asyncpg", "+psycopg2"))
with engine.connect() as conn:
    our_rows = conn.execute(text(
        "SELECT id, name, name_normalized FROM ingredients"
    )).fetchall()

our_norms = {(r[2] or normalize(r[1])): r[0] for r in our_rows}

# Exact match
matches = [(row["food_name"], row["name_norm"]) for _, row in df.iterrows()
           if row["name_norm"] in our_norms]

print(f"\n=== Exact match: {len(matches)} / {len(df)} INDB rows match our ingredients ===")
print(f"    Match rate: {len(matches)/len(df)*100:.1f}%")
if matches:
    print("Matched names (first 30):")
    for indb_name, norm in matches[:30]:
        print(f"  '{indb_name}'")
