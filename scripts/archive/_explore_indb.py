"""Explore INDB.xlsx structure before any DB changes."""
import os, sys
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

import pandas as pd

INDB_PATH = r"C:\Users\Lenovo\Desktop\Code\2026\Nutria\Mitihar_dietician\data\INDB\Indian-Nutrient-Databank-INDB--main\INDB.xlsx"

xl = pd.ExcelFile(INDB_PATH)
print("Sheets:", xl.sheet_names)

for sheet in xl.sheet_names:
    df = xl.parse(sheet)
    print(f"\n=== Sheet: '{sheet}' ({len(df)} rows × {len(df.columns)} cols) ===")
    print("Columns:", list(df.columns))
    if len(df) > 0:
        print("First 3 rows:")
        print(df.head(3).to_string())
