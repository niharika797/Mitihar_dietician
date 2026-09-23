"""Scan IFCT2017.pdf to find data table structure."""
import pdfplumber, re

PDF = r"C:\Users\Lenovo\Desktop\Code\2026\Nutria\Mitihar_dietician\IFCT2017.pdf"

# Keywords that indicate a data table page
DATA_KEYWORDS = ["kcal", "protein", "energy", "carbo", "fat", "fibre", "moisture"]

with pdfplumber.open(PDF) as pdf:
    total = len(pdf.pages)
    print(f"Total pages: {total}")

    # Scan pages 1-100 to find table start
    print("\n--- Scanning pages 1-150 for table content ---")
    table_pages = []
    for i in range(min(150, total)):
        text = pdf.pages[i].extract_text() or ""
        low = text.lower()
        hits = sum(1 for kw in DATA_KEYWORDS if kw in low)
        if hits >= 3:
            table_pages.append(i + 1)
            if len(table_pages) <= 3:
                print(f"\nPAGE {i+1} ({hits} keywords):")
                print(text[:800])
                print("---")

    print(f"\nPages with ≥3 data keywords (first 20): {table_pages[:20]}")

    # Once first table page found, look at next few pages
    if table_pages:
        fp = table_pages[0]
        print(f"\n--- Full text of page {fp} ---")
        print(pdf.pages[fp - 1].extract_text())

        # Check tables object extraction
        print(f"\n--- pdfplumber table extraction on page {fp} ---")
        tbls = pdf.pages[fp - 1].extract_tables()
        print(f"Tables found: {len(tbls)}")
        if tbls:
            t = tbls[0]
            print(f"Rows: {len(t)}, cols: {len(t[0]) if t else 0}")
            print("First 5 rows:")
            for row in t[:5]:
                print(f"  {row}")

        # Also try page after
        if fp < total:
            print(f"\n--- pdfplumber table extraction on page {fp+1} ---")
            tbls2 = pdf.pages[fp].extract_tables()
            print(f"Tables found: {len(tbls2)}")
            if tbls2:
                t2 = tbls2[0]
                print(f"Rows: {len(t2)}, cols: {len(t2[0]) if t2 else 0}")
                for row in t2[:5]:
                    print(f"  {row}")
