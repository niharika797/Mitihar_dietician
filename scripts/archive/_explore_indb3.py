"""Check bfp_manual source entries — are they raw ingredients?"""
import pandas as pd

INDB_PATH = r"C:\Users\Lenovo\Desktop\Code\2026\Nutria\Mitihar_dietician\data\INDB\Indian-Nutrient-Databank-INDB--main\INDB.xlsx"
df = pd.read_excel(INDB_PATH, sheet_name="Nutrient Data")

print("=== bfp_manual sample (first 30) ===")
bfp = df[df["primarysource"] == "bfp_manual"]["food_name"]
for n in bfp.head(30):
    print(f"  {n}")

print("\n=== open_source_recipes sample (first 15) ===")
osr = df[df["primarysource"] == "open_source_recipes"]["food_name"]
for n in osr.head(15):
    print(f"  {n}")

# Check what our 9 matched foods actually are vs their per-100g values
matched = ["vegetable stock", "idli", "poha", "pav bhaji masala", "green chutney",
           "tomato puree", "garam masala", "green chilli sauce", "tomato ketchup"]
print("\n=== Our 9 matched INDB entries — are they raw ingredients? ===")
mask = df["food_name"].str.lower().str.strip().isin(matched)
matched_df = df[mask][["food_name", "primarysource", "energy_kcal", "protein_g", "carb_g", "fat_g", "fibre_g"]]
print(matched_df.to_string())

# Also try word-level match to see potential coverage
print("\n=== Word-level match analysis ===")
import os, sys
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))
from dotenv import load_dotenv; load_dotenv()
from sqlalchemy import create_engine, text

engine = create_engine(os.environ["DATABASE_URL"].replace("+asyncpg", "+psycopg2"))
with engine.connect() as conn:
    our_rows = conn.execute(text("SELECT name FROM ingredients")).fetchall()
our_names = [r[0].lower().strip() for r in our_rows]

# For each INDB name, check if ANY of our ingredient names is a substring (bidirectional)
partial_matches = []
for _, row in df.iterrows():
    indb_norm = row["food_name"].lower().strip()
    for our_name in our_names:
        if our_name in indb_norm or indb_norm in our_name:
            if len(our_name) >= 4:  # avoid noise from short strings
                partial_matches.append((row["food_name"], our_name))
                break

print(f"Partial/substring matches: {len(partial_matches)} (first 20 shown)")
for indb_name, our_name in partial_matches[:20]:
    print(f"  INDB: '{indb_name}' ↔ OURS: '{our_name}'")
