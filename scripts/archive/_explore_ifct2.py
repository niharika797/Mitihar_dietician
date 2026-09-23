"""Find where actual food data tables start in IFCT2017.pdf."""
import pdfplumber, re

PDF = r"C:\Users\Lenovo\Desktop\Code\2026\Nutria\Mitihar_dietician\IFCT2017.pdf"

# Indicators of a data row (food code pattern like "A001" or numeric columns)
CODE_RE = re.compile(r'\b[A-Z]\d{3,4}\b')   # e.g. A001, B1234
NUM_RE  = re.compile(r'\b\d+\.\d+\b')        # decimal numbers like "365.2"

with pdfplumber.open(PDF) as pdf:
    total = len(pdf.pages)
    print(f"Scanning pages 50-300 for data tables...")

    hits = []
    for i in range(49, min(300, total)):
        text = pdf.pages[i].extract_text() or ""
        codes = len(CODE_RE.findall(text))
        nums  = len(NUM_RE.findall(text))
        if codes >= 3 and nums >= 10:
            hits.append((i+1, codes, nums))

    print(f"Pages with food codes + numbers: {len(hits)}")
    print("First 10:", hits[:10])

    if hits:
        # Print first hit in detail
        pg_num = hits[0][0]
        page = pdf.pages[pg_num - 1]
        print(f"\n--- Full text of page {pg_num} ---")
        print(page.extract_text())

        # Try table extraction
        print(f"\n--- Tables on page {pg_num} ---")
        tbls = page.extract_tables()
        print(f"Tables found: {len(tbls)}")
        if tbls:
            t = tbls[0]
            print(f"Shape: {len(t)} rows x {len(t[0])} cols")
            print("First 5 rows:")
            for row in t[:5]:
                print(f"  {row}")

        # Try 2nd hit too
        if len(hits) > 1:
            pg2 = hits[1][0]
            print(f"\n--- Full text of page {pg2} ---")
            print(pdf.pages[pg2-1].extract_text()[:1000])
            tbls2 = pdf.pages[pg2-1].extract_tables()
            print(f"Tables on page {pg2}: {len(tbls2)}")
            if tbls2:
                t2 = tbls2[0]
                print(f"Shape: {len(t2)} rows x {len(t2[0])} cols")
                for row in t2[:5]:
                    print(f"  {row}")
